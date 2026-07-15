"""Phase-4 label-coverage report: how much of our failure corpus carries a
usable label BEFORE (38-class only) vs AFTER (two-field vein+specific_failure).

This is the reproducible source of the Phase-4 headline number AND the command
the 4.2 final gate re-runs against the post-merge sellable CSV:

    python -m eval.label_coverage
    python -m eval.label_coverage --sellable trajectories/sellable_breakers_v2.csv

Nothing here re-runs episodes or the browser; it reads saved trajectories on
disk and re-derives labels with harness.failure_classifier.label_episode, which
is a thin wrapper over trajectories.vein_taxonomy.canonical_vein (the locked
tagger) — no vein logic is reimplemented.

Definitions (honest, per the scoping fix):
  * A failure is LABELED if it has a specific_failure (a forbidden trap fired)
    OR a meaningful behavioural agent_failure_class (anything but
    None / "unclassified_failure").
  * "no_forbidden_fired" is a NAMED residual (breaker task failed WITHOUT
    tripping its trap), not a bug — it is only counted unlabeled when its
    behavioural class is also unclassifiable.
  * Sellable coverage is reported separately: of break episodes on the sellable
    task set, what fraction get a specific_failure (target 100%).
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
from collections import Counter

from harness.failure_classifier import label_episode, audit_forbidden_invariant

_UNMEANINGFUL = {None, "", "unclassified_failure"}


def _load_episodes(traj_glob):
    """Yield (task_id, agent_failure_class, success, verifier_result) for every
    saved episode record that carries verifier_result.all_milestones."""
    paths = glob.glob(traj_glob + "/**/*.jsonl", recursive=True) + \
            glob.glob(traj_glob + "/**/*.json", recursive=True)
    for p in paths:
        if "__pycache__" in p:
            continue
        try:
            with open(p) as fh:
                d = json.load(fh)
        except Exception:
            continue
        for r in (d if isinstance(d, list) else [d]):
            if not isinstance(r, dict):
                continue
            vr = r.get("verifier_result")
            if r.get("task_id") and isinstance(vr, dict) and "all_milestones" in vr:
                yield r["task_id"], r.get("agent_failure_class"), vr.get("success"), vr


def _short(tid):
    return tid.split("/")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sellable", default="trajectories/sellable_breakers_v2.csv")
    ap.add_argument("--traj-glob", default="trajectories")
    args = ap.parse_args()

    sell, sell_full = set(), []
    try:
        with open(args.sellable) as fh:
            for r in csv.DictReader(fh):
                sell_full.append(r["task_id"])   # full id: build_suite needs it
                sell.add(_short(r["task_id"]))    # short id: matches episode ids
    except Exception as e:
        print(f"[warn] could not read sellable CSV {args.sellable}: {e}")

    fails = [(tid, old, vr) for tid, old, succ, vr in _load_episodes(args.traj_glob)
             if not succ]
    n = len(fails)
    if not n:
        print("no failure episodes found under", args.traj_glob)
        return

    rows = []
    for tid, old, vr in fails:
        lab = label_episode(tid, vr, fallback_class=old)
        rows.append((tid, old, lab["label_source"], lab["specific_failure"]))

    def labeled(r):
        _, old, _src, spec = r
        return bool(spec) or (old not in _UNMEANINGFUL)

    before = sum(1 for r in rows if r[1] in _UNMEANINGFUL)
    unlab = [r for r in rows if not labeled(r)]

    print(f"=== Phase-4 label coverage over {n} failure episodes "
          f"(glob={args.traj_glob}) ===")
    print(f"BEFORE (38-class only):    unlabeled {before}/{n} = {100*before/n:.1f}%")
    print(f"AFTER  (two-field+38cls):  unlabeled {len(unlab)}/{n} = {100*len(unlab)/n:.1f}%")
    print(f"           -> {before - len(unlab)} failures newly labeled")

    print("\nlabel_source distribution (AFTER):")
    for k, v in Counter(r[2] for r in rows).most_common():
        print(f"   {v:5d}  ({100*v/n:4.1f}%)  {k}")

    print("\nstill-unlabeled residual (LLM-judge target, 4.3):")
    for k, v in Counter(r[2] for r in unlab).most_common():
        print(f"   {v:4d}  {k}")

    # Sellable-scoped coverage + invariant guard (the 4.2 final gate)
    sb = [r for r in rows
          if _short(r[0]) in sell and r[2] in ("forbidden_milestone", "forbidden_multi")]
    cov = 100 * sum(1 for r in sb if r[3]) / max(len(sb), 1)
    print(f"\n=== SELLABLE set ({len(sell)} tasks) ===")
    print(f"break episodes on disk: {len(sb)}; specific_failure coverage = {cov:.1f}%")

    inv = audit_forbidden_invariant(sell_full)
    hist = Counter(inv.values())
    errs = {t: c for t, c in inv.items() if not isinstance(c, int)}
    multi = {t: c for t, c in inv.items() if isinstance(c, int) and c > 1}
    print(f"forbidden-count invariant over sellable set: {dict(sorted(hist.items(), key=str))}")
    if errs:
        print(f"  [ERROR] could not build {len(errs)} sellable task(s) — invariant NOT verified: "
              f"{dict(list(errs.items())[:5])}{' ...' if len(errs) > 5 else ''}")
    elif multi:
        print(f"  [warn] multi-forbidden sellable tasks (specific_failure is '+'-joined): {multi}")
    elif hist and set(hist) == {1}:
        print(f"  OK: all {sum(hist.values())} sellable tasks have exactly 1 forbidden milestone")
    else:
        print(f"  [warn] unexpected forbidden-count distribution: {dict(hist)}")


if __name__ == "__main__":
    main()
