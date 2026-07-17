"""Authentication helpers for the private ``/_harness/*`` control plane.

The token is provisioned through the process environment.  It is deliberately
never copied into browser context state, task prompts, trajectories, or files.
"""

from __future__ import annotations

import os
import secrets


HARNESS_TOKEN_ENV = "HARNESS_TOKEN"
HARNESS_TOKEN_HEADER = "X-Harness-Token"


def get_harness_token() -> str:
    """Return the provisioned token, failing closed when absent."""
    token = os.environ.get(HARNESS_TOKEN_ENV, "")
    if not token:
        raise RuntimeError(f"{HARNESS_TOKEN_ENV} is not configured")
    return token


def ensure_harness_token() -> str:
    """Provision one random token for this process tree when needed."""
    token = os.environ.get(HARNESS_TOKEN_ENV, "")
    if not token:
        token = secrets.token_urlsafe(32)
        os.environ[HARNESS_TOKEN_ENV] = token
    return token


def harness_headers() -> dict[str, str]:
    """Headers for trusted runner-side HTTP clients."""
    return {HARNESS_TOKEN_HEADER: get_harness_token()}
