"""OpenAI RAW-COORDINATE browser agent — no Set-of-Mark (multi-tab + async).

The OpenAI twin of :class:`PixelCoordAgent`. Same perception as the Anthropic
coord agent — a PLAIN screenshot with NO numbered marks and NO accessibility
manifest — and the same raw-coordinate action space (``click_at(x, y)`` etc.),
but driven through an OpenAI-COMPATIBLE chat-completions endpoint instead of the
Anthropic API. It reuses ``TOOLS_COORD`` + the coord ``SYSTEM_PROMPT`` from
``pixel_coord_agent`` so the two agents differ ONLY in the model backend — which
is exactly what makes a cross-model leaderboard on the SAME modality (raw pixel
grounding) apples-to-apples.

Same multi-tab tools, same ``wait`` action, same ``eval_mode`` (no reward
leakage), same async ``tick()`` at turn-start, so it runs the multi-tab async
tasks (M14+) unchanged.

Reads OPENAI_API_KEY (or a provider key via base_url) from the environment.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from harness.runner import BrowserCtx
from agents.pixel_coord_agent import TOOLS_COORD, SYSTEM_PROMPT
from agents.openai_pixel_agent import _to_openai_tools


# Raw-coordinate tools in OpenAI function-calling format.
TOOLS_OPENAI_COORD = _to_openai_tools(TOOLS_COORD)


class OpenAICoordAgent:
    """gpt-* raw-coordinate browser agent (no SoM) over an OpenAI-compatible
    endpoint, with multi-tab + async tools.

    Pass ``model`` to override the default. Set OPENAI_API_KEY (or base_url +
    the provider key) in env.
    """

    def __init__(self, model: str | None = None, max_steps: int | None = None,
                 verbose: bool = True, base_url: str | None = None,
                 api_key: str | None = None, eval_mode: bool | None = None):
        from openai import OpenAI
        base = base_url or os.getenv("OPENAI_BASE_URL") or None
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base, api_key=key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # Step budget — default 50, overridable via AGENT_MAX_STEPS (parity with
        # PixelCoordAgent so a cross-model run can share one cap).
        self.max_steps = (max_steps if max_steps is not None
                          else int(os.getenv("AGENT_MAX_STEPS", "50")))
        self.verbose = verbose
        # No reward leakage in benchmark runs (AGENT_EVAL_MODE=1): strip
        # milestone names + running score from the agent's observation. The
        # trajectory still records them for grading.
        self.eval_mode = (eval_mode if eval_mode is not None
                          else os.getenv("AGENT_EVAL_MODE", "0") == "1")

    async def run(self, ctx: BrowserCtx, task_brief: str) -> None:
        messages: list[dict[str, Any]] = [
            {"role": "system",
             "content": SYSTEM_PROMPT + f"\n\n## TASK\n\n{task_brief}"},
        ]
        last_result = "(this is your first turn)"

        for turn in range(self.max_steps):
            # ── TICK the async clock BEFORE observing (events scheduled for
            # this step arrive + show in the screenshot the agent acts on). ──
            await ctx.tick()
            # ── OBSERVE: a PLAIN screenshot of the active tab (NO marks) ──
            raw_png = await ctx.page.screenshot(full_page=False)
            b64 = base64.standard_b64encode(raw_png).decode("ascii")
            try:
                tabs = await ctx._tab_strip()
            except Exception:
                tabs = []

            user_text = (
                f"URL: {ctx.page.url}\n"
                f"Open tabs: {json.dumps(tabs)}\n"
                f"Task: {task_brief}\n\n"
                f"Last action result: {last_result}"
            )
            messages.append({"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]})

            # ── THINK + ACT ──
            # tool_choice="required" forces an ACTION every turn (small models
            # otherwise narrate the plan as prose and never emit a tool call).
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, max_completion_tokens=4096,
                    tools=TOOLS_OPENAI_COORD, tool_choice="required",
                    messages=messages,
                )
            except Exception as e:
                if self.verbose:
                    print(f"[openai_coord] API error: {type(e).__name__}: {e}")
                break

            msg = resp.choices[0].message
            usage = resp.usage
            tin = int(getattr(usage, "prompt_tokens", 0) or 0)
            tout = int(getattr(usage, "completion_tokens", 0) or 0)
            text = msg.content or ""
            tool_calls = msg.tool_calls or []

            if not tool_calls:
                if self.verbose:
                    print(f"[openai_coord] no tool call. text={text[:160]}")
                messages.append({"role": "assistant", "content": text})
                break

            tc = tool_calls[0]
            kind = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            # Persist ONLY the first tool_call so an extra/parallel one never
            # goes unanswered (OpenAI 400s on a tool_call with no tool message).
            messages.append({"role": "assistant", "content": text,
                "tool_calls": [{"id": tc.id, "type": "function",
                    "function": {"name": kind,
                                 "arguments": tc.function.arguments or "{}"}}]})
            if self.verbose:
                print(f"[openai_coord] step {turn}: {kind}({json.dumps(args)[:110]})")

            rec = None
            try:
                if kind == "click_at":
                    rec = await ctx.click_xy(int(args["x"]), int(args["y"]),
                                             reasoning=args.get("reason", ""))
                elif kind == "type_at":
                    rec = await ctx.type_xy(int(args["x"]), int(args["y"]),
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
                elif kind == "wait":
                    rec = await ctx.wait(reasoning=args.get("reason", ""))
                elif kind == "finish":
                    if self.verbose:
                        print(f"[openai_coord] finishing: {args.get('reason', '')}")
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
                    elif self.eval_mode:
                        last_result = f"OK ({kind}). URL now {rec.url_after}."
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
                    print(f"[openai_coord] {last_result}")

            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": last_result})
