# -*- coding: utf-8 -*-
"""Phase 1.1 — compute the unscreened backlog.

backlog = { tasks with a forbidden milestone (the 185) }
          minus { tasks already in trajectories/coverage_matrix.csv (the 74) }

Writes trajectories/unscreened_backlog.csv with columns:
    task_id, slug, primary_vein_tag

primary_vein_tag is derived by the repository's canonical taxonomy.

Sort order: the FOUR gap categories first (implicit-constraint, self-contradiction,
source-anchoring, ask-don't-guess), then the remaining veins.
"""
import csv
import os
from server.verifiers import SUITE_FACTORIES
from trajectories.vein_taxonomy import canonical_vein

COVERAGE = "trajectories/coverage_matrix.csv"
OUT = "trajectories/unscreened_backlog.csv"

GAP_TAGS = ["implicit-constraint", "self-contradiction", "source-anchoring", "ask-dont-guess"]


def forbidden_tasks() -> set[str]:
    out = set()
    for tid, fac in SUITE_FACTORIES.items():
        suite = fac()
        if any(getattr(m, "forbidden", False) for m in suite.milestones):
            out.add(tid)
    return out


def screened_tasks() -> set[str]:
    out = set()
    if not os.path.exists(COVERAGE):
        return out
    with open(COVERAGE, newline="") as f:
        for row in csv.DictReader(f):
            tid = (row.get("task_id") or "").strip()
            if tid:
                out.add(tid)
    return out


def vein_tag(tid: str) -> str:
    return canonical_vein(tid)


def main():
    forb = forbidden_tasks()
    screened = screened_tasks()
    backlog = sorted(forb - screened)
    print(f"forbidden-milestone tasks: {len(forb)}")
    print(f"already in coverage_matrix: {len(screened)}")
    print(f"unscreened backlog:         {len(backlog)}")

    rows = []
    for tid in backlog:
        slug = tid.replace("/", "_")
        rows.append({"task_id": tid, "slug": slug, "primary_vein_tag": vein_tag(tid)})

    # sort: 4 gap categories first (in listed order), then other veins (alpha).
    def sort_key(r):
        tag = r["primary_vein_tag"]
        if tag in GAP_TAGS:
            return (0, GAP_TAGS.index(tag), r["task_id"])
        return (1, 0, r["task_id"] if tag else "", )  # other veins in the middle
    rows.sort(key=lambda r: (sort_key(r)[0], sort_key(r)[1], r["primary_vein_tag"], r["task_id"]))

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["task_id", "slug", "primary_vein_tag"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    dist = Counter(r["primary_vein_tag"] for r in rows)
    print(f"\n[wrote {OUT}] vein distribution of the backlog:")
    for tag in GAP_TAGS + sorted(set(dist) - set(GAP_TAGS)):
        if tag in dist:
            print(f"   {tag:20} {dist[tag]}")
    n_gap = sum(dist[t] for t in GAP_TAGS if t in dist)
    print(f"\n   4 gap-category tasks (screened first): {n_gap}")
    print(f"   remaining (other veins):               {len(rows) - n_gap}")


if __name__ == "__main__":
    main()
