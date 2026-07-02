# -*- coding: utf-8 -*-
"""Phase 0.4 gate check — parse the oracle trajectories and prove every task's
hand-coded gold solver scores EXACTLY 1.00 on all 3 seeds.

A sub-1.00 oracle means the task's own gold solution can't satisfy its verifier —
the task is broken (unsolvable as written), not hard. Such tasks must be fixed or
pulled before any model is screened, else a model "failure" on them is meaningless.

Reads trajectories/oracle_phase0/ (the isolated Phase-0 run dir). Dedupes on
(task_id, seed) — if an episode ran more than once, ALL copies must be 1.00.
"""
import glob
import json
import sys
from collections import defaultdict

from server.verifiers import SUITE_FACTORIES

SEEDS = {0, 1, 2}
DIR = "trajectories/oracle_phase0"
EPS = 1e-9


def main():
    expected_tasks = set(SUITE_FACTORIES.keys())
    # (task, seed) -> list of (score, success, episode_id, error)
    seen = defaultdict(list)
    files = sorted(glob.glob(f"{DIR}/*.jsonl"))
    for f in files:
        try:
            d = json.load(open(f))
        except Exception as e:
            print(f"   !! unparseable trajectory {f}: {e}")
            continue
        tid = d.get("task_id")
        seed = d.get("seed")
        vr = d.get("verifier_result") or {}
        seen[(tid, seed)].append((
            vr.get("score"), vr.get("success"), d.get("episode_id"), d.get("error"),
        ))

    print(f"parsed {len(files)} trajectory files -> {len(seen)} (task,seed) cells\n")

    missing = []          # (task, seed) expected but absent
    not_perfect = []      # (task, seed, score, success, error)
    dupes = []            # (task, seed, n)

    for tid in sorted(expected_tasks):
        for seed in sorted(SEEDS):
            recs = seen.get((tid, seed))
            if not recs:
                missing.append((tid, seed))
                continue
            if len(recs) > 1:
                dupes.append((tid, seed, len(recs)))
            for score, success, _eid, error in recs:
                if score is None or abs(score - 1.0) > EPS or not success:
                    not_perfect.append((tid, seed, score, success, error))

    # tasks that appeared but aren't in the registry (shouldn't happen)
    extra = sorted({t for (t, s) in seen} - expected_tasks)

    print("=== COVERAGE ===")
    print(f"   expected: {len(expected_tasks)} tasks x {len(SEEDS)} seeds = "
          f"{len(expected_tasks) * len(SEEDS)} cells")
    print(f"   missing cells: {len(missing)}")
    for x in missing[:30]:
        print("   !! MISSING", x)
    if extra:
        print(f"   !! trajectories for unknown task ids: {extra[:20]}")

    print("\n=== ORACLE PERFECTION (every cell must score exactly 1.00) ===")
    print(f"   non-1.00 cells: {len(not_perfect)}")
    for tid, seed, score, success, error in not_perfect[:60]:
        print(f"   !! {tid} seed={seed} score={score} success={success} err={error}")

    print(f"\n   (info) {len(dupes)} (task,seed) cells ran more than once "
          f"(all copies checked): {dupes[:10]}")

    summary = {
        "dir": DIR,
        "n_files": len(files),
        "n_cells": len(seen),
        "expected_cells": len(expected_tasks) * len(SEEDS),
        "missing": missing,
        "not_perfect": not_perfect,
        "extra_task_ids": extra,
        "dupes": dupes,
    }
    with open("trajectories/_oracle_gate_check.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    ok = not missing and not not_perfect and not extra
    print("\n=== SUMMARY ===")
    print(f"ORACLE GATE: {'PASS — all 234 tasks score 1.00 on all 3 seeds' if ok else 'FAIL — see above'}")
    print("[wrote trajectories/_oracle_gate_check.json]")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
