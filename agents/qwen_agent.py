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

VALIDATED on OpenRouter (2026-06): the Qwen3-VL family drives the browser
end-to-end (vision + forced tool-calling). Model-support gotchas found live:
  * qwen/qwen3-vl-30b-a3b-instruct  -> WORKS (vision + tools + tool_choice=required)
  * qwen/qwen3-vl-235b-a22b-instruct, qwen/qwen3-vl-8b-instruct -> also WORK
  * qwen/qwen2.5-vl-72b-instruct    -> NO tool-use endpoint on OpenRouter (unusable)
  * qwen/qwen3-vl-32b-instruct      -> tools yes, but rejects tool_choice="required"
So default to a known-good Qwen3-VL model when pointed at OpenRouter.
"""

from __future__ import annotations

import os

from agents.openai_pixel_agent import OpenAIPixelAgent

_DEFAULT_DASHSCOPE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
_DEFAULT_MODEL_DASHSCOPE = "qwen-vl-plus"
# Known-good on OpenRouter (supports vision + tools + forced tool_choice).
_DEFAULT_MODEL_OPENROUTER = "qwen/qwen3-vl-30b-a3b-instruct"


class QwenAgent(OpenAIPixelAgent):
    """SoM + multi-tab + async agent driven by a Qwen-VL model over an
    OpenAI-compatible endpoint."""

    def __init__(self, model: str | None = None, max_steps: int | None = None,
                 verbose: bool = True, eval_mode: bool | None = None):
        base_url = os.getenv("QWEN_BASE_URL") or _DEFAULT_DASHSCOPE
        api_key = (os.getenv("QWEN_API_KEY")
                   or os.getenv("DASHSCOPE_API_KEY")
                   or os.getenv("OPENROUTER_API_KEY"))
        # Pick a default model that matches the endpoint, so `--agent qwen` with no
        # --model works out-of-the-box (the DashScope default 404s on OpenRouter).
        default_model = (_DEFAULT_MODEL_OPENROUTER if "openrouter" in base_url
                         else _DEFAULT_MODEL_DASHSCOPE)
        # max_steps=None -> the parent reads AGENT_MAX_STEPS (120 for the hard
        # tasks); a hard default here would silently cap every Qwen run at 50.
        super().__init__(
            model=model or os.getenv("QWEN_MODEL", default_model),
            max_steps=max_steps, verbose=verbose,
            base_url=base_url, api_key=api_key, eval_mode=eval_mode)
