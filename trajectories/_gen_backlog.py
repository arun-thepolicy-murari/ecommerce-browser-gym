# -*- coding: utf-8 -*-
"""Phase 1.1 — compute the unscreened backlog.

backlog = { tasks with a forbidden milestone (the 185) }
          minus { tasks already in trajectories/coverage_matrix.csv (the 74) }

Writes trajectories/unscreened_backlog.csv with columns:
    task_id, slug, primary_vein_tag

primary_vein_tag is derived exactly the way the differentiator analysis did it:
regex the task's factory docstring (server/tasks.py, via TASKS[tid].__doc__) for vein
keywords, in priority order; if none match, fall back to checkout-pattern keywords.

Sort order: the FOUR gap categories first (implicit-constraint, self-contradiction,
source-anchoring, ask-don't-guess), then the remaining veins, then checkout — so the
information gap gets screened before the checkout-tagged backlog.
"""
import csv
import os
import re

from server.tasks import TASKS
from server.verifiers import SUITE_FACTORIES

COVERAGE = "trajectories/coverage_matrix.csv"
OUT = "trajectories/unscreened_backlog.csv"

# keyword (regex, matched case-insensitive against the docstring) -> canonical tag.
# Ordered by priority: the 4 gap categories first so a task carrying several cues is
# tagged by the gap vein it belongs to.
# Patterns are matched (case-insensitively, via .upper()) against the docstring.
# NOTE on ask-dont-guess: the naive `ABSTENTION|AMBIGU` overcounts badly —
#   * bare "ABSTENTION" is ALSO used by the infeasibility vein
#     (M36 = "IMPOSSIBILITY / ABSTENTION"), a different failure mechanism, so we
#     require the literal "ASK-DON'T-GUESS" phrase instead of bare ABSTENTION;
#   * "AMBIGU" substring-matches "UNAMBIGUOUS" (the OPPOSITE signal, e.g.
#     "…mapping is unambiguous" in M230/M53/M62), so we use \bAMBIGUOUS\b whose
#     word boundary already excludes UNAMBIGUOUS (belt-and-suspenders (?<!UN)).
VEIN_RULES = [
    ("implicit-constraint",  r"IMPLICIT[- ]?CONSTRAINT"),
    ("self-contradiction",   r"SELF[- ]?CONTRADICTION"),
    ("source-anchoring",     r"SOURCE[- ]?ANCHORING"),
    ("ask-dont-guess",       r"ASK[- ]?DON'?T[- ]?GUESS|(?<!UN)\bAMBIGUOUS\b"),
    ("sycophancy",           r"SYCOPHAN"),
    ("tool-affordance",      r"TOOL[- ]?AFFORDANCE"),
    ("structural",           r"STRUCTURAL"),
    ("injection",            r"INJECTION"),
    ("infeasibility",        r"INFEASIBIL|IMPOSSIBIL"),
]
GAP_TAGS = ["implicit-constraint", "self-contradiction", "source-anchoring", "ask-dont-guess"]

# checkout-pattern fallback keywords -> "checkout" (the vein most of the built breakers
# already sit in). Only consulted when no vein keyword above matched.
CHECKOUT_RE = re.compile(
    r"ADD[- ]?ON|PROTECTION PLAN|PRESELECT|SNEAK|COUPON|EXPIRED|CORPORATE CARD|"
    r"GIFT|QUANTITY|QTY|SHIP[- ]?TO|CHECKOUT|CART|REORDER|SUBSCRIPTION|CADENCE",
    re.I)


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
    doc = (TASKS[tid].__doc__ or "")
    up = doc.upper()
    for tag, pat in VEIN_RULES:
        if re.search(pat, up):
            return tag
    if CHECKOUT_RE.search(doc):
        return "checkout"
    return "checkout"     # default bucket — the built breakers' home vein


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

    # sort: 4 gap categories first (in listed order), then other veins (alpha),
    # then checkout; ties broken by task_id.
    def sort_key(r):
        tag = r["primary_vein_tag"]
        if tag in GAP_TAGS:
            return (0, GAP_TAGS.index(tag), r["task_id"])
        if tag == "checkout":
            return (2, 0, r["task_id"])
        return (1, 0, r["task_id"] if tag else "", )  # other veins in the middle
    rows.sort(key=lambda r: (sort_key(r)[0], sort_key(r)[1], r["primary_vein_tag"], r["task_id"]))

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["task_id", "slug", "primary_vein_tag"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    dist = Counter(r["primary_vein_tag"] for r in rows)
    print(f"\n[wrote {OUT}] vein distribution of the backlog:")
    for tag in GAP_TAGS + sorted(set(dist) - set(GAP_TAGS) - {"checkout"}) + ["checkout"]:
        if tag in dist:
            print(f"   {tag:20} {dist[tag]}")
    n_gap = sum(dist[t] for t in GAP_TAGS if t in dist)
    print(f"\n   4 gap-category tasks (screened first): {n_gap}")
    print(f"   remaining (other veins + checkout):    {len(rows) - n_gap}")


if __name__ == "__main__":
    main()
