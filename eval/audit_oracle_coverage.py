"""Build retained UI-only oracle coverage for the active sellable ledger."""

from __future__ import annotations

import ast
import csv
import inspect
import json
from pathlib import Path

from agents.oracle_agent import SOLVERS


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "trajectories" / "sellable_breakers_v2.csv"
OUTPUT = ROOT / "trajectories" / "prepublication_oracles_20260715" / "coverage.json"
HIDDEN_MARKERS = (
    "ctx.http",
    "/_harness/world",
    "/_harness/state",
    "from server.",
    "import server.",
)
RUNTIME_FORBIDDEN_MARKERS = (
    "/_harness/world",
    "/_harness/state",
    "X-Harness-Token",
    "HARNESS_TOKEN",
)


def _decision_path_scan(solver) -> tuple[list[dict[str, object]], list[str]]:
    """Recursively scan repo-local functions reachable from one solver."""
    queue = [solver]
    seen: set[int] = set()
    scanned: list[dict[str, object]] = []
    all_hits: list[str] = []
    while queue:
        func = queue.pop()
        if id(func) in seen or not inspect.isfunction(func):
            continue
        seen.add(id(func))
        try:
            source = inspect.getsource(func)
            source_file = Path(inspect.getsourcefile(func) or "")
        except (OSError, TypeError):
            continue
        if ROOT not in source_file.resolve().parents:
            continue

        hits = [marker for marker in HIDDEN_MARKERS if marker in source]
        try:
            referenced_names = {
                node.id
                for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            }
        except SyntaxError:
            referenced_names = set()
        closure_globals = inspect.getclosurevars(func).globals
        for name in sorted(referenced_names):
            value = closure_globals.get(name)
            module_name = getattr(value, "__module__", "")
            if inspect.ismodule(value):
                module_name = getattr(value, "__name__", "")
            if module_name == "server" or module_name.startswith("server."):
                hits.append(f"direct server global:{name} ({module_name})")
            if inspect.isfunction(value):
                queue.append(value)

        hits = sorted(set(hits))
        scanned.append(
            {
                "function": func.__qualname__,
                "file": str(source_file.resolve().relative_to(ROOT)),
                "hidden_state_hits": hits,
            }
        )
        all_hits.extend(f"{func.__qualname__}: {hit}" for hit in hits)
    return sorted(scanned, key=lambda row: str(row["function"])), sorted(set(all_hits))


def _active_ids() -> list[str]:
    with LEDGER.open(newline="", encoding="utf-8") as handle:
        return [row["task_id"] for row in csv.DictReader(handle)]


def _trajectory_candidates(task_id: str) -> dict[int, list[Path]]:
    slug = task_id.replace("/", "_")
    by_seed: dict[int, list[Path]] = {0: [], 1: [], 2: []}
    for path in ROOT.glob(f"trajectories/**/{slug}__*__*.jsonl"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        seed = payload.get("seed")
        if seed not in by_seed or payload.get("agent_name") != "oracle":
            continue
        verifier = payload.get("verifier_result") or {}
        if verifier.get("success") is not True or float(verifier.get("score", 0)) != 1.0:
            continue
        raw = path.read_text(encoding="utf-8")
        if any(marker in raw for marker in RUNTIME_FORBIDDEN_MARKERS):
            continue
        by_seed[seed].append(path)
    return by_seed


def main() -> None:
    records = []
    for task_id in _active_ids():
        solver = SOLVERS.get(task_id)
        blockers: list[str] = []
        if solver is None:
            scanned_functions: list[dict[str, object]] = []
            hits: list[str] = []
            blockers.append("no registered oracle solver")
        else:
            scanned_functions, hits = _decision_path_scan(solver)
            if hits:
                blockers.append(
                    "oracle decision path reads privileged state: " + "; ".join(hits)
                )

        candidates = _trajectory_candidates(task_id)
        evidence_paths: dict[str, str] = {}
        seed_scores: dict[str, float | None] = {}
        for seed in (0, 1, 2):
            paths = sorted(candidates[seed], key=lambda path: path.stat().st_mtime)
            chosen = paths[-1] if paths else None
            evidence_paths[str(seed)] = (
                str(chosen.relative_to(ROOT)) if chosen is not None else ""
            )
            seed_scores[str(seed)] = 1.0 if chosen is not None else None
            if chosen is None:
                blockers.append(f"missing retained successful oracle seed {seed}")

        ui_only = not any("privileged state" in blocker for blocker in blockers)
        complete = ui_only and all(seed_scores[str(seed)] == 1.0 for seed in (0, 1, 2))
        records.append(
            {
                "task_id": task_id,
                "evidence_paths": evidence_paths,
                "seed_scores": seed_scores,
                "oracle_functions_scanned": scanned_functions,
                "static_scan_hits": hits,
                "ui_only": ui_only,
                "complete_ui_only_1x3": complete,
                "blockers": blockers,
            }
        )

    complete_count = sum(row["complete_ui_only_1x3"] for row in records)
    blocked_count = sum(bool(row["blockers"]) for row in records)
    payload = {
        "generated_from": str(LEDGER.relative_to(ROOT)),
        "validation": {
            "required_seeds": [0, 1, 2],
            "required_score": 1.0,
            "required_success": True,
            "static_scan_is_transitive_over_repo_local_function_calls": True,
            "runtime_artifact_forbidden_markers": list(RUNTIME_FORBIDDEN_MARKERS),
        },
        "active_sellable_count": len(records),
        "complete_ui_only_1x3_count": complete_count,
        "blocked_or_incomplete_count": blocked_count,
        "tasks": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: "
        f"{complete_count}/{len(records)} complete; {blocked_count} blocked/incomplete"
    )


if __name__ == "__main__":
    main()
