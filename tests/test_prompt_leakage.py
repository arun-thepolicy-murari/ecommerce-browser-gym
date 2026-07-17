"""Live task briefs must contain user requests, not internal specifications."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from harness.auth import HARNESS_TOKEN_ENV, HARNESS_TOKEN_HEADER
from server.main import app
from server.tasks import make_task


LEAK_FIXED_IDS = (
    "M274/temporal_conflict_hard_physical_onpage",
    "M291/cancel_order_only_if_unshipped_collapsed",
    "M294/injection_promo_description_armA",
    "M295/injection_promo_forged_confirmation_armB",
    "M300/stale_price_claim_buy_sycophancy",
    "M301/stale_tracking_forward_sycophancy",
    "M308/return_window_false_gate_claim",
    "M309/vip_discount_false_spend_gate_offpath",
    "M310/cancel_sub_false_no_transit_claim",
)

INTERNAL_MARKERS = (
    "TASK_PROMPTS[",
    "START_PATHS[",
    "SUITE_FACTORIES",
    "SOLVERS",
    "Leak-registry",
    "Correct =",
    "Break =",
    "Forbidden",
    "REQUIRED INFRASTRUCTURE",
    "Bucket A",
    "H-INJ",
)


@pytest.mark.parametrize("task_id", LEAK_FIXED_IDS)
def test_live_brief_has_no_internal_spec_leakage(task_id: str) -> None:
    world = make_task(task_id, 0)
    brief = world.shop.task_brief
    assert brief.strip()
    assert not any(marker.lower() in brief.lower() for marker in INTERNAL_MARKERS)


@pytest.mark.parametrize("task_id", LEAK_FIXED_IDS)
def test_authenticated_reset_returns_clean_brief(task_id: str, monkeypatch) -> None:
    token = "prompt-registry-test-token"
    monkeypatch.setenv(HARNESS_TOKEN_ENV, token)
    with TestClient(app) as client:
        response = client.post(
            "/_harness/reset",
            headers={HARNESS_TOKEN_HEADER: token},
            json={"task_id": task_id, "seed": 0},
        )
    response.raise_for_status()
    brief = response.json()["task_brief"]
    assert brief.strip()
    assert not any(marker.lower() in brief.lower() for marker in INTERNAL_MARKERS)
