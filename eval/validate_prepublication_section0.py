"""Strict reconciliation checks for pre-publication protocol Section 0."""

from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import re

from server.tasks import TASKS
from trajectories.vein_taxonomy import canonical_vein


ROOT = Path(__file__).resolve().parents[1]
TRAJ = ROOT / "trajectories"
OUT_DIR = TRAJ / "prepublication_validation_20260715"
LEAK_IDS = {
    "M274", "M291", "M294", "M295", "M300",
    "M301", "M308", "M309", "M310",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check_markdown_links(path: Path) -> list[str]:
    failures = []
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        clean = target.split("#", 1)[0]
        if clean and not (path.parent / clean).resolve().exists():
            failures.append(f"{path.relative_to(ROOT)} -> {target}")
    return failures


def main() -> None:
    with (TRAJ / "sellable_breakers_v2.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        sellable_ids = [row["task_id"] for row in csv.DictReader(handle)]
    assert len(sellable_ids) == len(set(sellable_ids)) == 85
    assert set(sellable_ids) <= set(TASKS)
    assert not {task.split("/", 1)[0] for task in sellable_ids} & LEAK_IDS
    assert "M56/gift_errand" not in sellable_ids

    coverage_path = TRAJ / "prepublication_oracles_20260715" / "coverage.json"
    coverage = _load(coverage_path)
    coverage_ids = [row["task_id"] for row in coverage["tasks"]]
    assert coverage_ids == sellable_ids
    assert coverage["active_sellable_count"] == 85
    assert coverage["complete_ui_only_1x3_count"] == 85
    assert coverage["blocked_or_incomplete_count"] == 0
    for row in coverage["tasks"]:
        assert row["ui_only"] and row["complete_ui_only_1x3"]
        assert row["blockers"] == [] and row["static_scan_hits"] == []
        for seed in ("0", "1", "2"):
            assert row["seed_scores"][seed] == 1.0
            evidence = ROOT / row["evidence_paths"][seed]
            assert evidence.exists()
            payload = _load(evidence)
            assert payload["task_id"] == row["task_id"]
            assert payload["seed"] == int(seed)
            assert payload["agent_name"] == "oracle"
            assert payload["verifier_result"]["success"] is True
            assert payload["verifier_result"]["score"] == 1.0

    brief_validation = _load(
        TRAJ
        / "prepublication_prompt_fix_20260715"
        / "brief_registry_validation.json"
    )
    assert brief_validation["registry_count"] == 312
    assert brief_validation["brief_count"] == 312
    assert brief_validation["archive_heading_count"] == 312
    assert brief_validation["exact_set_equality"] is True
    assert brief_validation["empty_prompt_keys"] == []

    superseded = _load(
        TRAJ
        / "prepublication_prompt_fix_20260715"
        / "historical_runs_superseded.json"
    )
    assert superseded["status"] == "INVALID_SUPERSEDED_PROMPT_LEAK"
    assert set(superseded["task_short_ids"]) == LEAK_IDS

    forensic = _load(
        TRAJ / "prepublication_m37_20260715" / "cascade" / "FORENSIC.json"
    )
    for tier in ("qwen", "gpt-5.1", "gpt-5.5"):
        assert forensic["tiers"][tier]["valid_seeds"] == 3
        assert forensic["tiers"][tier]["breaks"] == 3
    assert forensic["tiers"]["sonnet"]["invalid"] == 3
    assert forensic["terminal_status"] == "BLOCKED_ANTHROPIC_CREDIT"

    token_marker_hits = []
    for path in (
        TRAJ / "prepublication_m37_20260715"
    ).glob("**/*.jsonl"):
        raw = path.read_text(encoding="utf-8")
        if "X-Harness-Token" in raw or "HARNESS_TOKEN" in raw:
            token_marker_hits.append(str(path.relative_to(ROOT)))
    for path in (
        TRAJ / "prepublication_oracles_20260715"
    ).glob("**/*.jsonl"):
        raw = path.read_text(encoding="utf-8")
        if "X-Harness-Token" in raw or "HARNESS_TOKEN" in raw:
            token_marker_hits.append(str(path.relative_to(ROOT)))
    assert token_marker_hits == []

    docs = [
        ROOT / "docs" / "PRE_PUBLICATION_VALIDATION_PROTOCOL.md",
        *sorted((ROOT / "docs" / "history" / "audits").glob("*2026-07-15.md")),
    ]
    link_failures = [
        failure for path in docs for failure in _check_markdown_links(path)
    ]
    assert link_failures == []

    distribution = dict(sorted(Counter(canonical_vein(task) for task in sellable_ids).items()))
    output = {
        "section": 0,
        "active_sellable_count": len(sellable_ids),
        "active_sellable_distribution": distribution,
        "oracle_coverage": "85/85",
        "oracle_blockers": 0,
        "prompt_registry_count": 312,
        "prompt_registry_exact_parity": True,
        "m37_terminal_status": forensic["terminal_status"],
        "m37_valid_breaks": {
            tier: forensic["tiers"][tier]["breaks"]
            for tier in ("qwen", "gpt-5.1", "gpt-5.5")
        },
        "m56_hold_preserved": True,
        "m346_credit_blocker_preserved_in_project_info": (
            "M346" in (ROOT / "PROJECT_INFO.md").read_text(encoding="utf-8")
            and "credit" in (ROOT / "PROJECT_INFO.md").read_text(encoding="utf-8").lower()
        ),
        "token_marker_hits_in_prepublication_trajectories": token_marker_hits,
        "markdown_link_failures": link_failures,
    }
    assert output["m346_credit_blocker_preserved_in_project_info"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "reconciliation.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
