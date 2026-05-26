"""Qwen (cheap, widely-used) browser agent via an OpenAI-COMPATIBLE endpoint.

Qwen-VL is served through OpenAI-compatible APIs (Alibaba DashScope or
OpenRouter), so this is a thin specialisation of :class:`OpenAIPixelAgent`
that points the client at a Qwen endpoint and defaults to a Qwen-VL model.
Same SoM perception, same multi-tab + `wait` tools, same `eval_mode` (no
reward leakage), same async `tick()` at turn-start — so it runs the multi-tab
ASYNC tasks (M14+) unchanged.

Configure via env (one of):

  DashScope (Alibaba, native Qwen):
    QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    QWEN_API_KEY=<dashscope key>            (--model qwen-vl-plus / qwen2.5-vl-*)

  OpenRouter (proxies Qwen + many models):
    QWEN_BASE_URL=https://openrouter.ai/api/v1
    QWEN_API_KEY=<openrouter key>           (--model qwen/qwen2.5-vl-72b-instruct)

NOTE: built per request as "agent only" — it is UNVALIDATED end-to-end until a
live Qwen key is supplied. The structure mirrors the working OpenAI agent, so
wiring should hold, but vision + tool-calling must be confirmed on the first
real run before trusting leaderboard numbers.
"""

from __future__ import annotations

import os

from agents.openai_pixel_agent import OpenAIPixelAgent

_DEFAULT_QWEN_MODEL = "qwen-vl-plus"
_DEFAULT_DASHSCOPE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


class QwenAgent(OpenAIPixelAgent):
    """SoM + multi-tab + async agent driven by a Qwen-VL model over an
    OpenAI-compatible endpoint."""

    def __init__(self, model: str | None = None, max_steps: int = 50,
                 verbose: bool = True, eval_mode: bool | None = None):
        base_url = os.getenv("QWEN_BASE_URL") or _DEFAULT_DASHSCOPE
        api_key = (os.getenv("QWEN_API_KEY")
                   or os.getenv("DASHSCOPE_API_KEY")
                   or os.getenv("OPENROUTER_API_KEY"))
        super().__init__(
            model=model or os.getenv("QWEN_MODEL", _DEFAULT_QWEN_MODEL),
            max_steps=max_steps, verbose=verbose,
            base_url=base_url, api_key=api_key, eval_mode=eval_mode)
