"""Protocol §3A — invalid_reason enum wires traj + classify (not cosmetic)."""
from __future__ import annotations

import json
from pathlib import Path

from eval.cascade import classify
from eval.cascade_v2 import _is_inconclusive
from harness.invalid_episode import (
    INVALID_AGENT_PROVIDER,
    INVALID_BROWSER_CRASH,
    INVALID_REASONS,
    INVALID_RESET,
    INVALID_VERIFIER_UNAVAILABLE,
    is_valid_reason,
    reason_from_error,
)
from harness.runner import Trajectory


def test_enum_constants_stable():
    assert INVALID_RESET in INVALID_REASONS
    assert INVALID_AGENT_PROVIDER in INVALID_REASONS
    assert len(INVALID_REASONS) == 6
    assert is_valid_reason(INVALID_BROWSER_CRASH)
    assert not is_valid_reason("not_a_reason")
    assert not is_valid_reason(None)


def test_reason_from_error_provider_and_browser():
    assert reason_from_error("LLMCallError: Error code: 402") == INVALID_AGENT_PROVIDER
    assert reason_from_error("APIStatusError: Payment Required") == INVALID_AGENT_PROVIDER
    assert (
        reason_from_error("Error: Execution context was destroyed")
        == INVALID_BROWSER_CRASH
    )
    assert reason_from_error("benign ValueError: oops") is None


def test_trajectory_serializes_invalid_reason():
    traj = Trajectory(
        episode_id="abcd1234",
        task_id="M271/deadline_conflict_delivery",
        seed=0,
        agent_name="qwen[test]",
        started_at=0.0,
        invalid_reason=INVALID_AGENT_PROVIDER,
        invalid_detail="LLMCallError: credit",
    )
    payload = traj.to_json()
    assert payload["invalid_reason"] == INVALID_AGENT_PROVIDER
    assert payload["invalid_detail"] == "LLMCallError: credit"


def _write_traj(dir_path: Path, *, seed: int, **fields) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    base = {
        "episode_id": f"ep{seed}",
        "task_id": "M271/deadline_conflict_delivery",
        "seed": seed,
        "steps": [{"step_idx": 0}] if fields.pop("_has_steps", True) else [],
        "verifier_result": {
            "success": False,
            "all_milestones": [
                {
                    "name": "ordered_despite_conflict",
                    "forbidden": True,
                    "fired_at_step": fields.pop("_forbid_step", -1),
                }
            ],
        },
        "error": None,
        "invalid_reason": None,
    }
    base.update(fields)
    path = dir_path / f"M271_deadline_conflict_delivery__{seed}__ep{seed}.jsonl"
    path.write_text(json.dumps(base), encoding="utf-8")


def test_classify_invalid_bucket(tmp_path: Path):
    _write_traj(
        tmp_path,
        seed=0,
        invalid_reason=INVALID_AGENT_PROVIDER,
        _forbid_step=5,  # would be break if not invalid
        verifier_result={
            "success": True,  # even fake success must yield invalid
            "all_milestones": [],
        },
    )
    _write_traj(tmp_path, seed=1, _forbid_step=3)
    _write_traj(tmp_path, seed=2, _forbid_step=-1)
    cnt, rows = classify("M271/deadline_conflict_delivery", str(tmp_path))
    assert cnt["invalid"] == 1
    assert cnt["break"] == 1
    assert cnt["incomplete"] == 1
    by_seed = {r[0]: r[1] for r in rows}
    assert by_seed["0"] == "invalid"
    assert by_seed["1"] == "break"
    assert by_seed["2"] == "incomplete"


def test_classify_additive_without_invalid_reason(tmp_path: Path):
    """Absent invalid_reason, break/success/incomplete paths are unchanged.

    Proves the vertical slice adds an infra bucket only — it does not relabel
    ordinary sellable outcomes when the field is unset (legacy + valid eps).
    """
    _write_traj(tmp_path, seed=0, _forbid_step=3)  # break
    _write_traj(
        tmp_path,
        seed=1,
        verifier_result={"success": True, "all_milestones": []},
    )
    _write_traj(tmp_path, seed=2, _forbid_step=-1)  # incomplete
    cnt, rows = classify("M271/deadline_conflict_delivery", str(tmp_path))
    assert cnt.get("invalid", 0) == 0
    assert cnt["break"] == 1
    assert cnt["success"] == 1
    assert cnt["incomplete"] == 1
    by_seed = {r[0]: r[1] for r in rows}
    assert by_seed == {"0": "break", "1": "success", "2": "incomplete"}


def test_is_inconclusive_prefers_invalid_reason():
    assert _is_inconclusive({"invalid_reason": INVALID_VERIFIER_UNAVAILABLE, "steps": [1]})
    assert _is_inconclusive({"error": "LLMCallError: 402", "steps": [1]})
    assert not _is_inconclusive({"steps": [{"step_idx": 0}], "error": None})
