"""Static safety regression checks for the final validation sample."""

from __future__ import annotations

import inspect

import pytest

from agents.oracle_agent import SOLVERS


SAMPLED_TASKS = (
    "M37/false_overcharge",
    "M103/mixed_basket_expired",
    "M56/gift_errand",
    "M115/wrong_item_warranty_then_reorder_dead_card",
    "M346/candidate_addresses_must_not_be_exposed",
    "M362/therapy_event_blocks_delivery_disclosure",
    "M211/cancel_shipped_then_confirm",
)


@pytest.mark.parametrize("task_id", SAMPLED_TASKS)
def test_sampled_oracle_does_not_read_hidden_harness_state(task_id: str) -> None:
    """Gold paths may use browser actions, never hidden harness-state reads."""
    source = inspect.getsource(SOLVERS[task_id])
    assert "/_harness/world" not in source
    assert "ctx.http" not in source

