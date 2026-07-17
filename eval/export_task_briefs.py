"""Export the live task registry briefs and exact-set validation metadata."""

from __future__ import annotations

import json
from pathlib import Path

from server.tasks import TASKS, make_task


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs" / "history" / "snapshots" / "ALL_TASK_BRIEFS.md"
VALIDATION = (
    ROOT
    / "trajectories"
    / "prepublication_prompt_fix_20260715"
    / "brief_registry_validation.json"
)
SUPERSEDED = VALIDATION.with_name("historical_runs_superseded.json")
LEAK_FIXED_SHORT_IDS = (
    "M274", "M291", "M294", "M295", "M300",
    "M301", "M308", "M309", "M310",
)


def main() -> None:
    registry_ids = list(TASKS)
    briefs: dict[str, str] = {}
    for task_id in registry_ids:
        built = make_task(task_id, 0)
        state = built.shop if hasattr(built, "shop") else built
        briefs[task_id] = state.task_brief

    lines = [f"# All Task Briefs ({len(briefs)})", ""]
    for task_id, brief in briefs.items():
        lines.extend((f"## {task_id}", "", brief, ""))
    ARCHIVE.write_text("\n".join(lines), encoding="utf-8")

    heading_ids = [
        line[3:]
        for line in ARCHIVE.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]
    payload = {
        "registry_count": len(registry_ids),
        "registry_ids": registry_ids,
        "brief_count": len(briefs),
        "brief_ids": list(briefs),
        "archive_heading_count": len(heading_ids),
        "archive_unique_heading_count": len(set(heading_ids)),
        "archive_ids": heading_ids,
        "empty_prompt_keys": [task_id for task_id, brief in briefs.items() if not brief.strip()],
        "tasks_missing_brief": sorted(set(registry_ids) - set(briefs)),
        "brief_ids_missing_task": sorted(set(briefs) - set(registry_ids)),
        "archive_missing_task": sorted(set(registry_ids) - set(heading_ids)),
        "archive_extra_task": sorted(set(heading_ids) - set(registry_ids)),
        "exact_set_equality": (
            registry_ids == list(briefs) == heading_ids
            and len(registry_ids) == len(set(registry_ids))
        ),
    }
    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    superseded_paths = sorted(
        {
            str(path.relative_to(ROOT))
            for short_id in LEAK_FIXED_SHORT_IDS
            for path in (ROOT / "trajectories").glob(f"**/{short_id}_*__*.jsonl")
        }
    )
    SUPERSEDED.write_text(
        json.dumps(
            {
                "status": "INVALID_SUPERSEDED_PROMPT_LEAK",
                "task_short_ids": list(LEAK_FIXED_SHORT_IDS),
                "historical_trajectory_count": len(superseded_paths),
                "historical_trajectory_paths": superseded_paths,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"exported {len(briefs)} briefs; exact_set_equality="
        f"{payload['exact_set_equality']}; empty={len(payload['empty_prompt_keys'])}"
    )


if __name__ == "__main__":
    main()
