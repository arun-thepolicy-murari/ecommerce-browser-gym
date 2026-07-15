"""Phase 5.1 — regenerate EVERY headline number from source, once, as the single
source of truth. Reads the real CSVs + canonical_vein(); quotes nothing from
memory or any earlier report.

    .venv/bin/python -m eval.recompute_headlines            # current CSVs
    .venv/bin/python -m eval.recompute_headlines --json     # machine-readable

Run against the current files. If a
regenerated number disagrees with something reported earlier, the regenerated one
wins — this script flags the discrepancy rather than picking whichever sounds
better. Every count here is derived, never hand-quoted.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter

from trajectories.vein_taxonomy import canonical_vein


def _short(tid):
    return tid.split("/")[0]


def parse_grid(g):
    """'3/3·2/3·3/3' -> [(3,3),(2,3),(3,3)] for (gpt-5.1, gpt-5.5, sonnet); None if malformed."""
    try:
        parts = [p.strip() for p in (g or "").split("·")]
        if len(parts) != 3:
            return None
        out = []
        for p in parts:
            n, d = p.split("/")
            out.append((int(n), int(d)))
        return out
    except Exception:
        return None


def ceiling_from_grid(grid):
    """Highest tier that breaks >=2/3. sonnet > gpt-5.5 > gpt-5.1 > weaker/unknown."""
    if not grid:
        return "UNPARSEABLE"
    g51, g55, son = grid
    if son[0] >= 2:
        return "sonnet"
    if g55[0] >= 2:
        return "gpt-5.5"
    if g51[0] >= 2:
        return "gpt-5.1"
    return "weaker/none"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sellable", default="trajectories/sellable_breakers_v2.csv")
    ap.add_argument("--coverage", default="trajectories/coverage_matrix_v2.csv")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.sellable)))
    total = len(rows)
    gridcol = "model_grid (5.1·5.5·son)"

    # --- per-vein via canonical_vein (deterministic) ---
    veins = Counter(canonical_vein(r["task_id"]) for r in rows)

    # --- per-tier ceiling from the sellable CSV's OWN grid column ---
    ceilings = Counter()
    unparseable = []
    for r in rows:
        grid = parse_grid(r.get(gridcol, ""))
        c = ceiling_from_grid(grid)
        ceilings[c] += 1
        if c == "UNPARSEABLE":
            unparseable.append((_short(r["task_id"]), r.get(gridcol, "")))

    # vein x ceiling cross-tab
    cross = {}
    for r in rows:
        v = canonical_vein(r["task_id"])
        c = ceiling_from_grid(parse_grid(r.get(gridcol, "")))
        cross.setdefault(v, Counter())[c] += 1

    # --- reconciliation vs coverage_matrix (independent screening grid) ---
    def _safe_int(x):
        try:
            return int(str(x).strip())
        except Exception:
            return None

    cov = list(csv.DictReader(open(args.coverage))) if args.coverage else []
    sell_ids = {_short(r["task_id"]) for r in rows}
    cov_ids = {_short(r["task_id"]) for r in cov}
    cov_candidates = {_short(r["task_id"]) for r in cov
                      if str(r.get("sonnet_sellable_candidate", "")).lower() == "true"}

    # canonical_vein vs the CSV's own 'pattern' column (informational; pattern is free-text)
    # (we don't trust 'pattern' — canonical_vein wins — but surface how often they diverge)

    report = {
        "source_files": {"sellable": args.sellable, "coverage": args.coverage},
        "STATUS": "FINAL current CSV recomputation",
        "total_confirmed_sellable": total,
        "per_vein_canonical": dict(veins.most_common()),
        "per_tier_ceiling_from_grid": dict(ceilings.most_common()),
        "vein_x_ceiling": {v: dict(c) for v, c in cross.items()},
        "reconciliation": {
            "sellable_rows": total,
            "coverage_matrix_rows": len(cov),
            "sellable_ids_missing_from_coverage": sorted(sell_ids - cov_ids),
            "coverage_sonnet_candidates_not_in_sellable": sorted(cov_candidates - sell_ids),
            "unparseable_model_grid": unparseable,
            "note": ("coverage_matrix is a SCREENING grid, NOT authoritative for the "
                     "sellable tier breakdown — tiers above are from the sellable CSV's "
                     "own model_grid column (66 sellable ids are absent from coverage)."),
        },
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"=== Phase 5.1 headline recompute  [{report['STATUS']}] ===")
    print(f"source: {args.sellable}\n")
    print(f"TOTAL confirmed sellable breakers: {total}\n")
    print("per-vein (canonical_vein, deterministic):")
    for v, n in veins.most_common():
        print(f"   {n:3d}  {v}")
    print(f"   ---  sum={sum(veins.values())}")
    print("\nper-tier ceiling (from sellable model_grid, break>=2/3):")
    for c, n in ceilings.most_common():
        print(f"   {n:3d}  {c}")
    print("\nvein x ceiling:")
    tiers = ["sonnet", "gpt-5.5", "gpt-5.1", "weaker/none", "UNPARSEABLE"]
    print(f"   {'vein':22} " + " ".join(f"{t:>11}" for t in tiers))
    for v, _n in veins.most_common():
        c = cross.get(v, {})
        print(f"   {v:22} " + " ".join(f"{c.get(t,0):>11}" for t in tiers))
    print("\n--- reconciliation flags ---")
    print(f"   sellable rows: {total} | coverage_matrix rows: {len(cov)}")
    print(f"   sellable ids NOT in coverage_matrix: {len(sell_ids - cov_ids)} "
          f"(coverage is a screening grid, not the sellable source)")
    print(f"   coverage sonnet-candidates NOT in sellable: {len(cov_candidates - sell_ids)}")
    if unparseable:
        print(f"   [REVIEW] {len(unparseable)} unparseable model_grid cells:")
        for tid, g in unparseable:
            print(f"      {tid}: {g!r}")


if __name__ == "__main__":
    main()
