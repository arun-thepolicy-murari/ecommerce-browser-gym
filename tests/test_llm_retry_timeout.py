"""Phase 0.6 — deterministic proof that a stuck LLM call can no longer hang.

These pin the guarantees of :mod:`agents._llm_retry`: a call that would block
forever becomes a *bounded* :class:`LLMCallError` in well under the time the raw
call would have blocked; transient errors are retried; plain 4xx client errors
are not. No network, no API key, no browser — pure logic, fast.
"""
from __future__ import annotations

import time

import pytest

from agents._llm_retry import acall, LLMCallError, is_retryable


async def test_hang_becomes_bounded_error():
    """A call that never returns in time raises LLMCallError quickly, instead of
    freezing the episode (and the whole screening batch) indefinitely."""
    def hang():
        time.sleep(2.0)          # simulate a stuck socket / non-returning proxy
        return "unreached"

    t0 = time.monotonic()
    with pytest.raises(LLMCallError):
        await acall(hang, label="hang", attempts=2, per_call_timeout=0.2,
                    base_delay=0.05, max_delay=0.05)
    elapsed = time.monotonic() - t0
    # 2 attempts x 0.2s ceiling + one ~0.05s backoff ~= 0.45s. Must be far below
    # the 2s a single raw call would have blocked — and infinitely below "forever".
    assert elapsed < 1.5, f"guard did not bound the hang (took {elapsed:.2f}s)"


async def test_transient_error_is_retried_then_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutError("transient stall")
        return "ok"

    out = await acall(flaky, label="flaky", attempts=3, per_call_timeout=1.0,
                      base_delay=0.01, max_delay=0.01)
    assert out == "ok"
    assert calls["n"] == 2       # failed once, retried, succeeded


async def test_client_4xx_is_not_retried():
    calls = {"n": 0}

    class BadRequest(Exception):
        status_code = 400        # malformed request — retrying can't help

    def bad():
        calls["n"] += 1
        raise BadRequest("malformed tool_use/tool_result pairing")

    with pytest.raises(BadRequest):
        await acall(bad, label="bad", attempts=3, per_call_timeout=1.0)
    assert calls["n"] == 1       # surfaced immediately, no wasted retries


async def test_exhausted_retries_raises_hard_error():
    calls = {"n": 0}

    def always_5xx():
        calls["n"] += 1
        raise type("ServerError", (Exception,), {"status_code": 503})("down")

    with pytest.raises(LLMCallError):
        await acall(always_5xx, label="down", attempts=3, per_call_timeout=1.0,
                    base_delay=0.01, max_delay=0.01)
    assert calls["n"] == 3       # retried the full budget, then hard-failed


def test_is_retryable_matrix():
    assert is_retryable(TimeoutError())
    assert is_retryable(type("E", (Exception,), {"status_code": 500})())
    assert is_retryable(type("E", (Exception,), {"status_code": 429})())
    assert not is_retryable(type("E", (Exception,), {"status_code": 400})())
    assert not is_retryable(type("E", (Exception,), {"status_code": 404})())
