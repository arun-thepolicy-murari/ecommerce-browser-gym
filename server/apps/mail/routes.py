"""Mail app routes — the ``/mail`` route family.

Mounted on the SAME FastAPI server as the shop (route-prefix sub-site), so
the harness's single ``server_url`` + reset + verify pipeline is reused
unchanged. To avoid a circular import (main imports this module; this
module must not import main), the handles it needs — the Jinja templates,
the world accessor, the context builder, the flash helper — are INJECTED
once at startup via :func:`configure`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.apps.mail import mutations as M

router = APIRouter(prefix="/mail", tags=["mail"])

# Injected by server.main at import time.
_deps: dict[str, Any] = {}


def configure(*, templates, get_world, build_ctx, flash) -> None:
    _deps.update(
        templates=templates, get_world=get_world,
        build_ctx=build_ctx, flash=flash,
    )


def _render(request: Request, name: str, **extra):
    ctx = _deps["build_ctx"](request, active_app="mail", **extra)
    return _deps["templates"].TemplateResponse(request, name, ctx)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def inbox(request: Request, q: str = ""):
    mail = _deps["get_world"]().mail
    emails = M.search_inbox(mail, q)
    return _render(request, "mail/inbox.html", mail=mail, emails=emails, q=q)


@router.get("/compose", response_class=HTMLResponse)
async def compose(request: Request, to: str = "", subject: str = ""):
    mail = _deps["get_world"]().mail
    return _render(
        request, "mail/compose.html",
        mail=mail, to_prefill=to, subject_prefill=subject,
    )


@router.get("/message/{email_id}", response_class=HTMLResponse)
async def message(request: Request, email_id: str):
    world = _deps["get_world"]()
    mail = world.mail
    M.mark_read(mail, email_id)            # opening == reading
    email = mail.get(email_id)
    if email is None:
        # Recoverable, like the shop's smart 404s: flash + back to inbox.
        _deps["flash"](world.shop, "error", "That email could not be found.")
        return RedirectResponse("/mail", 303)
    return _render(request, "mail/message.html", mail=mail, email=email)


@router.post("/send")
async def send(
    request: Request,
    to: str = Form(""),
    subject: str = Form(""),
    body: str = Form(""),
):
    world = _deps["get_world"]()
    r = M.send_email(world.mail, to=to, subject=subject, body=body)
    if r.get("ok"):
        _deps["flash"](world.shop, "success", f"Email sent to {r['to']}.")
        return RedirectResponse("/mail?sent=1", 303)
    _deps["flash"](world.shop, "error", r.get("error", "Could not send email."))
    return RedirectResponse("/mail/compose", 303)
