"""OpenAI-backed browser agent (GPT function-calling).

A thin sibling of :class:`agents.llm_agent.LLMBrowserAgent` (Anthropic): it
drives the SAME ``BrowserCtx`` through the SAME tool set + observation, but
via the OpenAI chat-completions function-calling API. Used for the
failure-mode harvest with a small / cheap model (default ``gpt-4o-mini``) —
weak enough to fail the cross-app tasks in interesting, recurring ways,
which is exactly what we want to mine.

Reads ``OPENAI_API_KEY`` from the environment. The key is NEVER hard-coded
or written to disk anywhere in this repo.
"""

from __future__ import annotations

import json
import os
from typing import Any

from harness.runner import BrowserCtx
from agents.llm_agent import SYSTEM_PROMPT, TOOLS_ANTHROPIC, LLMBrowserAgent


def _to_openai_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert our Anthropic tool specs to OpenAI function-tool specs so the
    two agents share ONE source of truth for the action space."""
    out: list[dict] = []
    for t in anthropic_tools:
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return out


TOOLS_OPENAI = _to_openai_tools(TOOLS_ANTHROPIC)


def _chat_request(model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a provider-aware chat request without changing OpenAI defaults."""
    is_openrouter = "openrouter.ai" in os.getenv("OPENAI_BASE_URL", "")
    request: dict[str, Any] = {
        "model": model,
        "tools": TOOLS_OPENAI,
        "tool_choice": "auto",
        "messages": messages,
    }
    if is_openrouter and model in {"tencent/hy3", "tencent/hy3:free"}:
        request["max_tokens"] = 2048
    else:
        request["max_completion_tokens"] = 2048
    if is_openrouter:
        request["extra_body"] = {
            "provider": {"require_parameters": True},
        }
    return request


async def _observation(ctx: BrowserCtx) -> str:
    """Reuse LLMBrowserAgent's observation builder (it doesn't touch self),
    so DOM-agent and GPT-agent see byte-identical observations — a fair
    comparison + zero duplication."""
    return await LLMBrowserAgent._observation(None, ctx)  # type: ignore[arg-type]


class OpenAIBrowserAgent:
    """A GPT-backed browser agent. Pass ``model`` to override
    (default gpt-4o-mini, or $OPENAI_MODEL)."""

    def __init__(self, model: str | None = None, max_steps: int = 30,
                 verbose: bool = True):
        from openai import OpenAI
        self.client = OpenAI()                     # reads OPENAI_API_KEY
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.4")
        self.max_steps = max_steps
        self.verbose = verbose
        self.cost_cap = float(os.getenv("AGENT_COST_CAP_USD", "0") or 0)
        self.cost_trip_fraction = float(
            os.getenv("AGENT_COST_TRIP_FRAC", "0.8") or 0.8
        )
        self.input_cost_per_m = float(
            os.getenv("AGENT_INPUT_COST_PER_M", "0") or 0
        )
        self.output_cost_per_m = float(
            os.getenv("AGENT_OUTPUT_COST_PER_M", "0") or 0
        )

    async def run(self, ctx: BrowserCtx, task_brief: str) -> None:
        messages: list[dict[str, Any]] = [
            {"role": "system",
             "content": SYSTEM_PROMPT + f"\n\nTASK: {task_brief}"},
        ]
        cumulative_cost = 0.0

        for turn in range(self.max_steps):
            messages.append({"role": "user", "content": await _observation(ctx)})

            resp = self.client.chat.completions.create(
                **_chat_request(self.model, messages)
            )
            msg = resp.choices[0].message
            usage = resp.usage
            tin = int(getattr(usage, "prompt_tokens", 0) or 0)
            tout = int(getattr(usage, "completion_tokens", 0) or 0)
            cumulative_cost += (
                tin * self.input_cost_per_m
                + tout * self.output_cost_per_m
            ) / 1_000_000
            text = msg.content or ""
            tool_calls = msg.tool_calls or []

            if not tool_calls:
                if self.verbose:
                    print(f"[openai_agent] no tool call. text={text[:200]}")
                messages.append({"role": "assistant", "content": text})
                break

            # Answer exactly ONE tool call per turn (keeps the
            # tool_call/tool_result protocol consistent).
            tc = tool_calls[0]
            kind = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}

            messages.append({
                "role": "assistant", "content": text,
                "tool_calls": [{
                    "id": tc.id, "type": "function",
                    "function": {"name": kind,
                                 "arguments": tc.function.arguments or "{}"},
                }],
            })
            if self.verbose:
                print(f"[openai_agent] step {turn}: {kind}({json.dumps(args)})")

            rec = None
            try:
                if kind == "navigate":
                    rec = await ctx.goto(args["path"], reasoning=args.get("reason", ""))
                elif kind == "click":
                    rec = await ctx.click(args["selector"], reasoning=args.get("reason", ""))
                elif kind == "fill":
                    rec = await ctx.fill(args["selector"], args["value"],
                                         reasoning=args.get("reason", ""))
                elif kind == "select":
                    rec = await ctx.select(args["selector"], args["value"],
                                           reasoning=args.get("reason", ""))
                elif kind == "check":
                    rec = await ctx.check(args["selector"], reasoning=args.get("reason", ""))
                elif kind == "submit":
                    rec = await ctx.submit(args["selector"], reasoning=args.get("reason", ""))
                elif kind == "open_tab":
                    rec = await ctx.open_tab(args["url"], reasoning=args.get("reason", ""))
                elif kind == "switch_tab":
                    rec = await ctx.switch_tab(int(args["index"]), reasoning=args.get("reason", ""))
                elif kind == "close_tab":
                    rec = await ctx.close_tab(int(args["index"]), reasoning=args.get("reason", ""))
                elif kind == "finish":
                    if self.verbose:
                        print(f"[openai_agent] finishing: {args.get('reason', '')}")
                    messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": json.dumps(
                            {"result": {"ok": True}, "current_url": ctx.page.url}),
                    })
                    break
                else:
                    raise ValueError(f"unknown tool {kind}")
                tool_result = {"ok": True}
            except Exception as e:
                tool_result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                if self.verbose:
                    print(f"[openai_agent] action failed: {tool_result}")

            if rec is not None:
                rec.raw_model_output = text
                rec.tokens_in = tin
                rec.tokens_out = tout

            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps(
                    {"result": tool_result, "current_url": ctx.page.url}),
            })
            if (self.cost_cap and
                    cumulative_cost >= self.cost_cap * self.cost_trip_fraction):
                if self.verbose:
                    print(
                        f"[openai_agent] cost watchdog trip at "
                        f"${cumulative_cost:.4f}"
                    )
                break
