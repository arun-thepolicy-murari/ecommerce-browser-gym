"""OpenAI (gpt-4o-mini) PIXEL / Set-of-Mark browser agent — multi-tab.

The GPT sibling of the Anthropic ``PixelBrowserAgent``. Same perception
(annotated screenshot + numbered marks via ``harness/som.py``), same
mark-id action space, but driven by an OpenAI vision model (default
gpt-4o-mini) AND extended with browser-tab tools so it can juggle the
multi-app workspace the way a person does.

Perception each turn:
  * a screenshot with numbered colored boxes on every interactable (SoM)
  * the current URL + the open-tabs strip + a text manifest of the marks
  * the task brief + the result of the last action
Actions (all mark-id or tab-index, never raw coordinates):
  click(mark) / type_text(mark,text) / key(name) / scroll(dir,px) /
  open_tab(url) / switch_tab(index) / close_tab(index) / finish

Reads OPENAI_API_KEY from the environment — never hard-coded.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from harness.runner import BrowserCtx
from harness.som import annotate_image, extract_marks, marks_to_manifest
from agents.pixel_agent import SYSTEM_PROMPT as _PIXEL_SYSTEM_PROMPT, TOOLS_PIXEL


# --------------------------------------------------------------------------- #
# Tools — the SoM pixel tools + browser-tab tools, in OpenAI format
# --------------------------------------------------------------------------- #

_TAB_TOOLS = [
    {"name": "open_tab",
     "description": ("Open an APP in a NEW browser tab and switch to it. "
                     "`url` is an app root: '/' (Shop), '/mail' (Mail), "
                     "'/food' (Food). Your old tab stays exactly where it "
                     "was — use this to keep one app open while you read "
                     "another."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string"}, "reason": {"type": "string"}},
         "required": ["url"]}},
    {"name": "switch_tab",
     "description": ("Make an already-open tab active by its index (see the "
                     "`tabs` list). Use this to flip BACK to a tab you "
                     "opened earlier."),
     "input_schema": {"type": "object", "properties": {
         "index": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["index"]}},
    {"name": "close_tab",
     "description": "Close an open tab by its index.",
     "input_schema": {"type": "object", "properties": {
         "index": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["index"]}},
]


def _to_openai_tools(anthropic_tools: list[dict]) -> list[dict]:
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": t["input_schema"]}}
            for t in anthropic_tools]


TOOLS_OPENAI_PIXEL = _to_openai_tools(TOOLS_PIXEL + _TAB_TOOLS)


# --------------------------------------------------------------------------- #
# System prompt — the pixel playbook + a multi-app/tabs addendum
# --------------------------------------------------------------------------- #

_MULTI_APP_TABS = """

═══════════════════════════════════════════════════════════════════════════
MULTI-APP WORKSPACE + BROWSER TABS
═══════════════════════════════════════════════════════════════════════════

At the very top of every page is a dark workspace bar with marks for
several apps: Shop, Mail, and Food. Some tasks span apps — e.g. place an
order in the Shop, then read the confirmation email in Mail and act on it.

You have THREE extra tools for tabs:
  open_tab(url)     open an app in a NEW tab and switch to it. `url` is an
                    app root: "/" (Shop), "/mail" (Mail), "/food" (Food).
  switch_tab(index) make an already-open tab active (see the `tabs` list).
  close_tab(index)  close a tab.

Each turn the message lists your open `tabs` as {index, url, title,
active}. Use tabs like a person on a multi-app task: keep the Shop in
tab 0, OPEN MAIL IN A SECOND TAB to read the confirmation email, then
switch_tab(0) BACK to the Shop to act on what you learned. (open_tab is the
ONE exception to "no navigation" — it only opens an app ROOT in a new tab;
WITHIN a tab you still navigate by clicking marks.)

CARRY VALUES ACCURATELY across tabs (an order number, a charged total, an
ETA). Read them off the screenshot of the OTHER app — never invent, guess,
or assume a value. If a task needs the exact total you were charged, you
must actually OPEN and READ the email; the sticker price on the product is
NOT the charged total.
"""

SYSTEM_PROMPT = _PIXEL_SYSTEM_PROMPT + _MULTI_APP_TABS


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #

class OpenAIPixelAgent:
    """gpt-4o-mini pixel/SoM agent with multi-tab tools."""

    def __init__(self, model: str | None = None, max_steps: int = 24,
                 verbose: bool = True):
        from openai import OpenAI
        self.client = OpenAI()                     # reads OPENAI_API_KEY
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.4")
        self.max_steps = max_steps
        self.verbose = verbose

    async def run(self, ctx: BrowserCtx, task_brief: str) -> None:
        messages: list[dict[str, Any]] = [
            {"role": "system",
             "content": SYSTEM_PROMPT + f"\n\n## TASK\n\n{task_brief}"},
        ]
        last_result = "(this is your first turn)"

        for turn in range(self.max_steps):
            # ── OBSERVE: marks + annotated screenshot + manifest + tabs ──
            marks = await extract_marks(ctx.page)
            raw_png = await ctx.page.screenshot(full_page=False)
            annotated = annotate_image(raw_png, marks)
            manifest = marks_to_manifest(marks)
            b64 = base64.standard_b64encode(annotated).decode("ascii")
            try:
                tabs = await ctx._tab_strip()
            except Exception:
                tabs = []

            user_text = (
                f"URL: {ctx.page.url}\n"
                f"Open tabs: {json.dumps(tabs)}\n"
                f"Task: {task_brief}\n\n"
                f"Visible marks ({len(marks)}):\n{manifest}\n\n"
                f"Last action result: {last_result}"
            )
            messages.append({"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]})

            # ── THINK + ACT ──
            # tool_choice="required" forces an ACTION every turn. Without it,
            # small models (gpt-4o-mini) tend to narrate the plan as prose and
            # never emit a tool call, stalling the episode at step 0.
            resp = self.client.chat.completions.create(
                model=self.model, max_completion_tokens=2048,
                tools=TOOLS_OPENAI_PIXEL, tool_choice="required",
                messages=messages,
            )
            msg = resp.choices[0].message
            usage = resp.usage
            tin = int(getattr(usage, "prompt_tokens", 0) or 0)
            tout = int(getattr(usage, "completion_tokens", 0) or 0)
            text = msg.content or ""
            tool_calls = msg.tool_calls or []

            if not tool_calls:
                if self.verbose:
                    print(f"[openai_pixel] no tool call. text={text[:160]}")
                messages.append({"role": "assistant", "content": text})
                break

            tc = tool_calls[0]
            kind = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            messages.append({"role": "assistant", "content": text,
                "tool_calls": [{"id": tc.id, "type": "function",
                    "function": {"name": kind,
                                 "arguments": tc.function.arguments or "{}"}}]})
            if self.verbose:
                print(f"[openai_pixel] step {turn}: {kind}({json.dumps(args)[:110]})")

            rec = None
            try:
                if kind == "click":
                    rec = await ctx.click_mark(int(args["mark_id"]), marks,
                                               reasoning=args.get("reason", ""))
                elif kind == "type_text":
                    rec = await ctx.type_into_mark(int(args["mark_id"]), marks,
                                                   args.get("text", ""),
                                                   reasoning=args.get("reason", ""))
                elif kind == "key":
                    rec = await ctx.key_press(args["name"],
                                              reasoning=args.get("reason", ""))
                elif kind == "scroll":
                    rec = await ctx.scroll_by(args["direction"],
                                              int(args["amount_px"]),
                                              reasoning=args.get("reason", ""))
                elif kind == "open_tab":
                    rec = await ctx.open_tab(args["url"],
                                             reasoning=args.get("reason", ""))
                elif kind == "switch_tab":
                    rec = await ctx.switch_tab(int(args["index"]),
                                               reasoning=args.get("reason", ""))
                elif kind == "close_tab":
                    rec = await ctx.close_tab(int(args["index"]),
                                              reasoning=args.get("reason", ""))
                elif kind == "finish":
                    if self.verbose:
                        print(f"[openai_pixel] finishing: {args.get('reason', '')}")
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": "OK (finished)."})
                    break
                else:
                    raise ValueError(f"unknown tool {kind}")

                if rec is not None:
                    rec.raw_model_output = text
                    rec.tokens_in = tin
                    rec.tokens_out = tout
                    if rec.action_error:
                        last_result = (f"ERROR: {rec.action_error}. "
                                       f"URL now {rec.url_after}.")
                    else:
                        last_result = (
                            f"OK ({kind}). URL now {rec.url_after}. "
                            f"Newly fired: {rec.milestones_fired_this_step or '[]'}. "
                            f"Score: {rec.running_score:.2f}.")
                else:
                    last_result = f"OK ({kind})."
            except Exception as e:
                last_result = f"DISPATCH ERROR: {type(e).__name__}: {e}"
                if self.verbose:
                    print(f"[openai_pixel] {last_result}")

            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": last_result})
