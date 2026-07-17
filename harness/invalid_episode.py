"""Machine-readable invalid-episode reasons (protocol §3A P0).

Invalid episodes must never count as break / success / incomplete in
``eval.cascade.classify``. See
``docs/history/audits/INVALID_EPISODE_ENUM_DESIGN_2026-07-16.md``.
"""
from __future__ import annotations

from typing import Final

# Exact strings — stable snake_case (v1 enum).
INVALID_RESET: Final = "invalid_reset"
INVALID_VERIFIER_UNAVAILABLE: Final = "invalid_verifier_unavailable"
INVALID_BROWSER_CRASH: Final = "invalid_browser_crash"
INVALID_AGENT_PROVIDER: Final = "invalid_agent_provider"
INVALID_EVENT_DELIVERY: Final = "invalid_event_delivery"
INVALID_INSTRUMENTATION: Final = "invalid_instrumentation"

INVALID_REASONS: Final[frozenset[str]] = frozenset({
    INVALID_RESET,
    INVALID_VERIFIER_UNAVAILABLE,
    INVALID_BROWSER_CRASH,
    INVALID_AGENT_PROVIDER,
    INVALID_EVENT_DELIVERY,
    INVALID_INSTRUMENTATION,
})

# Substrings matched against ``Trajectory.error`` / exception text.
# Prefer provider bucket for credit/auth/rate-limit (highest volume).
_PROVIDER_MARKERS: Final[tuple[str, ...]] = (
    "LLMCallError",
    "APIConnectionError",
    "APIStatusError",
    "APIError",
    "RateLimit",
    "Timeout",
    "context length",
    "Error code: 402",
    "Error code: 401",
    "Error code: 429",
    "Error code: 500",
    "Error code: 502",
    "Error code: 503",
    "Payment Required",
    "insufficient",
    "quota",
    "credit",
)

_BROWSER_MARKERS: Final[tuple[str, ...]] = (
    "Page.screenshot",
    "Execution context was destroyed",
    "Target closed",
    "Browser closed",
    "BrowserContext",
    "Playwright",
)

_VERIFIER_MARKERS: Final[tuple[str, ...]] = (
    "/_harness/verify",
    "verifier",
    "ConnectError",
    "RemoteProtocolError",
)


def is_valid_reason(reason: str | None) -> bool:
    return bool(reason) and reason in INVALID_REASONS


def reason_from_error(err: str | None) -> str | None:
    """Map an exception / traj.error string to an enum value, or None."""
    if not err:
        return None
    e = str(err)
    if any(m in e for m in _PROVIDER_MARKERS):
        return INVALID_AGENT_PROVIDER
    if any(m in e for m in _BROWSER_MARKERS):
        return INVALID_BROWSER_CRASH
    if any(m in e for m in _VERIFIER_MARKERS):
        return INVALID_VERIFIER_UNAVAILABLE
    return None
