"""Live browser service — CDP screencast out, input back-channel in.

This is what lets a human WATCH and DRIVE the same browser the agent uses. It is
deliberately a separate process from ``server.main``: the gym owns world state,
this owns a browser, and neither imports the other.

Wire contract
-------------
``POST /live/sessions``            open a browser session -> {session_id, ticket}
``WS   /live/stream/{session_id}`` frames out, input in (ticket required)
``POST /live/sessions/{id}/close`` reclaim

**Coordinates are NORMALIZED (0..1), never pixels.** The rendered canvas is almost
never the same size as the 1280x800 viewport, so shipping pixels would silently
mis-place every click. The client sends a fraction of its canvas; the service
multiplies by the real viewport. Scale bugs become impossible by construction.

Security (not deferred — a stream is a remote-control channel)
-------------------------------------------------------------
* short-lived HMAC ticket, scoped to session id + owner
* Origin allow-list on the websocket handshake
* exactly ONE controller at a time; extra viewers are read-only
* monotonic input ids, acknowledged back, so input order is observable
* tickets die with the session
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

VIEWPORT_W = int(os.getenv("LIVE_VIEWPORT_W", "1280"))
VIEWPORT_H = int(os.getenv("LIVE_VIEWPORT_H", "800"))
TICKET_TTL_S = int(os.getenv("LIVE_TICKET_TTL_S", "300"))
SECRET = os.getenv("LIVE_STREAM_SECRET", os.getenv("HARNESS_TOKEN", "dev-live-secret"))
# "*" allows any origin (dev only); otherwise a comma-separated allow-list.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("LIVE_ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app = FastAPI(title="live-browser")


# --------------------------------------------------------------------------- tickets
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_ticket(session_id: str, owner: str, ttl: int = TICKET_TTL_S) -> str:
    """A ticket authorises ONE session for ONE owner for a short window. Signed, so
    the service needs no shared session store to validate it.

    The owner is base64url-encoded: owners are emails, which contain dots, and a
    dot-delimited ticket would otherwise parse the wrong fields (it did).
    """
    exp = int(time.time()) + ttl
    payload = f"{session_id}:{owner}:{exp}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{exp}.{sig}.{_b64(owner.encode())}"


def check_ticket(session_id: str, ticket: str) -> str | None:
    """Returns the owner when valid, else None. Constant-time compare."""
    try:
        exp_s, sig, owner_b64 = ticket.split(".", 2)
        exp = int(exp_s)
        owner = _unb64(owner_b64).decode()
    except (ValueError, AttributeError, UnicodeDecodeError):
        return None
    if exp < time.time():
        return None
    expect = hmac.new(SECRET.encode(), f"{session_id}:{owner}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return owner if hmac.compare_digest(expect, sig) else None


def origin_ok(origin: str | None) -> bool:
    if "*" in ALLOWED_ORIGINS:
        return True
    return bool(origin) and origin in ALLOWED_ORIGINS


# --------------------------------------------------------------------------- session
@dataclass
class LiveSession:
    """One browser, owned for the life of a workspace."""

    id: str
    owner: str
    url: str
    pw: Any = None
    browser: Any = None
    context: Any = None
    page: Any = None
    cdp: Any = None
    # Latest-wins: a slow client must never grow an unbounded backlog, and a stale
    # frame is worthless — only the newest pixels matter.
    latest_frame: str | None = None
    frame_seq: int = 0
    frame_event: asyncio.Event = field(default_factory=asyncio.Event)
    controller: str | None = None          # ws id currently allowed to send input
    last_input_id: int = 0
    closed: bool = False

    async def start(self) -> None:
        from playwright.async_api import async_playwright

        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": VIEWPORT_W, "height": VIEWPORT_H},
            device_scale_factor=1,
        )
        self.page = await self.context.new_page()
        await self.page.goto(self.url, wait_until="load")
        self.cdp = await self.context.new_cdp_session(self.page)
        self.cdp.on("Page.screencastFrame", self._on_frame)
        await self.cdp.send("Page.startScreencast", {
            "format": "jpeg", "quality": 60,
            "maxWidth": VIEWPORT_W, "maxHeight": VIEWPORT_H, "everyNthFrame": 1,
        })

    def _on_frame(self, params: dict) -> None:
        # Ack FIRST — Chromium stops emitting until the previous frame is
        # acknowledged, so an un-acked frame silently freezes the stream.
        sid = params.get("sessionId")
        if sid is not None and self.cdp is not None:
            asyncio.create_task(self._ack(sid))
        self.latest_frame = params.get("data")
        self.frame_seq += 1
        self.frame_event.set()

    async def _ack(self, session_id: int) -> None:
        with contextlib.suppress(Exception):
            await self.cdp.send("Page.screencastFrameAck", {"sessionId": session_id})

    # --- input ------------------------------------------------------------
    def to_page_xy(self, nx: float, ny: float) -> tuple[float, float]:
        """Normalized (0..1) -> page pixels. This is the whole reason the wire
        format is fractional: the client canvas is scaled, the viewport is not."""
        nx = min(max(float(nx), 0.0), 1.0)
        ny = min(max(float(ny), 0.0), 1.0)
        return nx * VIEWPORT_W, ny * VIEWPORT_H

    async def click(self, nx: float, ny: float, button: str = "left", clicks: int = 1) -> None:
        x, y = self.to_page_xy(nx, ny)
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": x, "y": y, "button": "none"})
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y, "button": button, "clickCount": clicks})
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y, "button": button, "clickCount": clicks})

    async def move(self, nx: float, ny: float) -> None:
        x, y = self.to_page_xy(nx, ny)
        await self.cdp.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "none"})

    async def scroll(self, nx: float, ny: float, dy: float, dx: float = 0.0) -> None:
        x, y = self.to_page_xy(nx, ny)
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseWheel", "x": x, "y": y, "deltaX": dx, "deltaY": dy})

    async def type_text(self, text: str) -> None:
        await self.page.keyboard.type(text)

    async def key(self, key: str) -> None:
        await self.page.keyboard.press(key)

    async def navigate(self, url: str) -> None:
        await self.page.goto(url, wait_until="load")

    # --- structured actions ------------------------------------------------
    # Raw pointer input is how a HUMAN drives the browser; a committed trajectory
    # must be replayable without one. These mirror the agent harness's own
    # vocabulary and its "everything is pickable, no timeouts" strategy — try the
    # real interaction, fall back to JS activation — so a human-authored golden
    # reproduces identically when the agent harness replays it. Diverging here
    # would make manual trajectories unrunnable in the very benchmark they exist
    # to feed.
    async def resolve(self, locator: dict) -> str | None:
        """Turn a semantic locator into a CSS selector that matches RIGHT NOW.
        Ordered most-durable first; coordinates are not a locator and never
        appear here."""
        cands: list[str] = []
        if locator.get("testId"):
            cands.append(f"[data-test-id={json.dumps(locator['testId'])}]")
        if locator.get("id"):
            cands.append(f"#{locator['id']}")
        if locator.get("css"):
            cands.append(locator["css"])
        if locator.get("name"):
            cands.append(f"[name={json.dumps(locator['name'])}]")
        for sel in cands:
            with contextlib.suppress(Exception):
                if await self.page.evaluate("(s) => !!document.querySelector(s)", sel):
                    return sel
        # role+name is last: it needs a Playwright locator rather than a selector,
        # so we resolve it to a concrete element and hand back a unique handle.
        if locator.get("role") and locator.get("name"):
            with contextlib.suppress(Exception):
                loc = self.page.get_by_role(locator["role"], name=locator["name"]).first
                if await loc.count():
                    await loc.evaluate("(el) => el.setAttribute('data-replay-target', '1')")
                    return "[data-replay-target='1']"
        return None

    async def _js_activate(self, selector: str, kind: str, value: str | None = None) -> bool:
        """Reveal a present-but-hidden element and activate it via JS. Same
        contract as the agent harness: a genuinely absent element is the ONLY
        failure — never a timeout."""
        return bool(await self.page.evaluate(
            """([sel, kind, val]) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                try { el.scrollIntoView({block: 'center', inline: 'center'}); } catch (e) {}
                if (kind === 'fill') {
                    try { el.focus(); } catch (e) {}
                    const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
                    if (d && d.set) d.set.call(el, val); else el.value = val;
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                } else if (kind === 'select') {
                    let matched = false;
                    for (const o of (el.options || [])) {
                        if (o.value === val || (o.textContent || '').trim() === val) { el.value = o.value; matched = true; break; }
                    }
                    if (!matched) el.value = val;
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                } else if (kind === 'check') {
                    if (!el.checked) { el.checked = true; el.dispatchEvent(new Event('change', {bubbles: true})); }
                } else {
                    el.click();
                }
                return true;
            }""",
            [selector, kind, value],
        ))

    async def act(self, kind: str, locator: dict | None = None, args: dict | None = None) -> dict:
        """Execute ONE structured action. Returns what actually happened —
        including the selector that matched — so the caller can record the
        resolved target rather than re-guessing it later."""
        args = args or {}
        if kind == "navigate":
            await self.navigate(args["url"])
            return {"ok": True, "kind": kind, "resolved": {"url": self.page.url}}
        if kind == "press":
            await self.key(args.get("key", "Enter"))
            return {"ok": True, "kind": kind, "resolved": {}}

        sel = await self.resolve(locator or {})
        if sel is None:
            # Fail LOUDLY: a silently-skipped action produces a trajectory that
            # claims to do something it never did.
            return {"ok": False, "kind": kind, "error": "no element matched the locator", "resolved": {}}

        value = args.get("value")
        ok = False
        if kind == "click":
            loc = self.page.locator(sel).first
            with contextlib.suppress(Exception):
                if await loc.is_visible():
                    await loc.scroll_into_view_if_needed(timeout=2000)
                    await loc.click(timeout=5000)
                    ok = True
            if not ok:
                ok = await self._js_activate(sel, "click")
        elif kind in ("fill", "type"):
            ok = await self._js_activate(sel, "fill", value)
        elif kind in ("select", "select_option"):
            ok = await self._js_activate(sel, "select", value)
        elif kind == "check":
            ok = await self._js_activate(sel, "check")
        else:
            return {"ok": False, "kind": kind, "error": f"unsupported action {kind!r}", "resolved": {}}

        with contextlib.suppress(Exception):
            await self.page.evaluate("() => document.querySelectorAll('[data-replay-target]').forEach(e => e.removeAttribute('data-replay-target'))")
        return {"ok": ok, "kind": kind, "resolved": {"selector": sel, "url": self.page.url},
                **({} if ok else {"error": "element matched but did not activate"})}

    async def describe(self, nx: float, ny: float) -> dict:
        """Locator candidates for whatever is at this point, captured BEFORE an
        action is dispatched — afterwards the element may not exist."""
        x, y = self.to_page_xy(nx, ny)
        return await self.page.evaluate(
            """([x, y]) => {
                const el = document.elementFromPoint(x, y);
                if (!el) return {};
                const t = el.closest('[data-test-id],button,a,input,select,textarea,[role]') || el;
                return {
                    testId: t.getAttribute('data-test-id') || '',
                    id: t.id || '',
                    name: t.getAttribute('name') || '',
                    role: t.getAttribute('role') || t.tagName.toLowerCase(),
                    type: t.getAttribute('type') || '',
                    autocomplete: t.getAttribute('autocomplete') || '',
                    label: (t.getAttribute('aria-label') || '').slice(0, 120),
                    text: (t.textContent || '').trim().slice(0, 120),
                    tag: t.tagName.toLowerCase(),
                };
            }""",
            [x, y],
        )

    async def info(self) -> dict:
        pages = self.context.pages if self.context else []
        return {
            "url": self.page.url if self.page else "",
            "tabs": [p.url for p in pages],
            "activeTab": pages.index(self.page) if self.page in pages else 0,
            "viewport": {"width": VIEWPORT_W, "height": VIEWPORT_H},
            "frameSeq": self.frame_seq,
        }

    async def close(self) -> None:
        self.closed = True
        for closer in (
            lambda: self.cdp.send("Page.stopScreencast"),
            lambda: self.context.close(),
            lambda: self.browser.close(),
            lambda: self.pw.stop(),
        ):
            with contextlib.suppress(Exception):
                await closer()


SESSIONS: dict[str, LiveSession] = {}


# --------------------------------------------------------------------------- http
class OpenBody(BaseModel):
    url: str
    owner: str = "anonymous"


@app.post("/live/sessions")
async def open_session(body: OpenBody) -> dict:
    sid = uuid.uuid4().hex[:12]
    s = LiveSession(id=sid, owner=body.owner, url=body.url)
    try:
        await s.start()
    except Exception as exc:  # noqa: BLE001 — surface the real reason, don't leak a half-session
        await s.close()
        raise HTTPException(500, f"could not start live browser: {exc}") from exc
    SESSIONS[sid] = s
    return {"session_id": sid, "ticket": mint_ticket(sid, body.owner), "viewport": {"width": VIEWPORT_W, "height": VIEWPORT_H}}


@app.get("/live/sessions/{sid}")
async def session_info(sid: str) -> dict:
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "unknown session")
    return await s.info()


class ActBody(BaseModel):
    kind: str
    locator: dict | None = None
    args: dict | None = None
    ticket: str = ""


@app.post("/live/sessions/{sid}/act")
async def session_act(sid: str, body: ActBody) -> dict:
    """Execute one STRUCTURED action — the replay path. A committed trajectory is
    replayed through here, never through recorded pixels, so it survives layout
    change and can be re-run by the agent harness."""
    s = SESSIONS.get(sid)
    if not s or s.closed:
        raise HTTPException(404, "unknown session")
    if check_ticket(sid, body.ticket) is None:
        raise HTTPException(403, "invalid or expired ticket")
    return await s.act(body.kind, body.locator, body.args)


class DescribeBody(BaseModel):
    x: float
    y: float
    ticket: str = ""


@app.post("/live/sessions/{sid}/describe")
async def session_describe(sid: str, body: DescribeBody) -> dict:
    """Locator candidates at a normalized point, read BEFORE dispatch."""
    s = SESSIONS.get(sid)
    if not s or s.closed:
        raise HTTPException(404, "unknown session")
    if check_ticket(sid, body.ticket) is None:
        raise HTTPException(403, "invalid or expired ticket")
    return await s.describe(body.x, body.y)


@app.post("/live/sessions/{sid}/close")
async def close_session(sid: str) -> dict:
    s = SESSIONS.pop(sid, None)
    if not s:
        raise HTTPException(404, "unknown session")
    await s.close()
    return {"ok": True}


@app.get("/live/health")
async def health() -> dict:
    return {"ok": True, "sessions": len(SESSIONS)}


# --------------------------------------------------------------------------- ws
@app.websocket("/live/stream/{sid}")
async def stream(ws: WebSocket, sid: str, ticket: str = Query(default=""), control: bool = Query(default=True)):
    s = SESSIONS.get(sid)
    if s is None or s.closed:
        await ws.close(code=4404); return
    if not origin_ok(ws.headers.get("origin")):
        await ws.close(code=4403); return
    owner = check_ticket(sid, ticket)
    if owner is None or owner != s.owner:
        await ws.close(code=4401); return

    await ws.accept()
    ws_id = uuid.uuid4().hex[:8]
    # Exactly one controller: a second controller would interleave input with the
    # first and make the recorded trajectory unattributable.
    is_controller = False
    if control and s.controller is None:
        s.controller = ws_id
        is_controller = True
    await ws.send_text(json.dumps({
        "type": "hello", "sessionId": sid, "controller": is_controller,
        "viewport": {"width": VIEWPORT_W, "height": VIEWPORT_H},
    }))

    async def pump_frames() -> None:
        last = -1
        while not s.closed:
            if s.frame_seq != last and s.latest_frame:
                last = s.frame_seq
                await ws.send_text(json.dumps({"type": "frame", "seq": last, "data": s.latest_frame}))
            else:
                s.frame_event.clear()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(s.frame_event.wait(), timeout=1.0)

    pump = asyncio.create_task(pump_frames())
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            kind = msg.get("type")
            if kind == "ping":
                await ws.send_text(json.dumps({"type": "pong"})); continue
            if not is_controller:
                await ws.send_text(json.dumps({"type": "denied", "reason": "read-only viewer"})); continue

            input_id = int(msg.get("id", 0))
            if input_id <= s.last_input_id:      # replayed/out-of-order input is dropped
                await ws.send_text(json.dumps({"type": "ack", "id": input_id, "applied": False, "reason": "stale"}))
                continue
            s.last_input_id = input_id

            if kind == "click":
                await s.click(msg["nx"], msg["ny"], msg.get("button", "left"), int(msg.get("clicks", 1)))
            elif kind == "move":
                await s.move(msg["nx"], msg["ny"])
            elif kind == "scroll":
                await s.scroll(msg["nx"], msg["ny"], float(msg.get("dy", 0)), float(msg.get("dx", 0)))
            elif kind == "type":
                await s.type_text(msg.get("text", ""))
            elif kind == "key":
                await s.key(msg.get("key", ""))
            elif kind == "navigate":
                await s.navigate(msg.get("url", ""))
            else:
                await ws.send_text(json.dumps({"type": "ack", "id": input_id, "applied": False, "reason": "unknown"}))
                continue
            await ws.send_text(json.dumps({"type": "ack", "id": input_id, "applied": True}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        with contextlib.suppress(Exception):
            await ws.send_text(json.dumps({"type": "error", "detail": str(exc)}))
    finally:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump
        if is_controller and s.controller == ws_id:
            s.controller = None  # release control so the annotator can reconnect
