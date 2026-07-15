"""Audit the historical checkout split now promoted to canonical default veins.

The retired top-level ``checkout`` vein was split into:
  * Instrument-Default — instrument axis only
  * Content-Default    — content axis only
  * Stacked-Default    — both axes

The Content axis includes wrong destination, message, schedule, and genuinely
unrequested basket additions (items, add-ons, services, or quantities).
The adjudicated 42-task mapping now lives in ``trajectories.vein_taxonomy`` and
is the single source consumed here.

    python -m eval.checkout_instrument_content
    python -m eval.checkout_instrument_content --sellable trajectories/sellable_breakers_v2.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "trajectories"))

from vein_taxonomy import DEFAULT_VEIN_BY_SHORT_ID, canonical_vein  # noqa: E402


def classify(tid: str) -> dict:
    label = DEFAULT_VEIN_BY_SHORT_ID.get(tid.split("/", 1)[0], "")
    has_i = label in {"instrument-default", "stacked-default"}
    has_c = label in {"content-default", "stacked-default"}
    return {
        "task_id": tid,
        "short": tid.split("/")[0],
        "label": label,
        "has_instrument": has_i,
        "has_content": has_c,
    }


def audited_default_ids(sellable_path: Path) -> list[str]:
    rows = list(csv.DictReader(sellable_path.open()))
    return [
        r["task_id"]
        for r in rows
        if r["task_id"].split("/", 1)[0] in DEFAULT_VEIN_BY_SHORT_ID
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--sellable",
        type=Path,
        default=ROOT / "trajectories" / "sellable_breakers_v2.csv",
    )
    ap.add_argument("--csv-out", type=Path, default=None,
                    help="Optional path to write per-task classifications.")
    args = ap.parse_args(argv)

    ids = audited_default_ids(args.sellable)
    results = [classify(tid) for tid in ids]
    counts = Counter(r["label"] for r in results)
    by_label: dict[str, list[str]] = defaultdict(list)
    for r in results:
        by_label[r["label"]].append(r["short"])

    n = len(results)
    print(f"historical checkout tasks, now canonical defaults: {n}")
    print()
    order = ("instrument-default", "content-default", "stacked-default")
    for label in order:
        c = counts.get(label, 0)
        pct = (100.0 * c / n) if n else 0.0
        print(f"  {label:14s}  {c:2d}  ({pct:5.1f}%)")
        print(f"    {', '.join(by_label[label])}")
    print()
    print("definition:")
    print("  instrument-default = instrument axis only")
    print("  content-default    = content axis only")
    print("  stacked-default    = both axes")
    unclassified = [r["short"] for r in results if not r["label"]]
    if unclassified:
        print(f"\nERROR: tasks on neither axis: {', '.join(unclassified)}")
        return 1
    drift = [
        r["short"]
        for r in results
        if canonical_vein(r["task_id"]) != r["label"]
    ]
    if drift:
        print(f"\nERROR: canonical mapping drift: {', '.join(drift)}")
        return 1

    if args.csv_out:
        args.csv_out.parent.mkdir(parents=True, exist_ok=True)
        with args.csv_out.open("w", newline="") as fh:
            w = csv.DictWriter(
                fh,
                fieldnames=["task_id", "short", "label",
                            "has_instrument", "has_content"],
            )
            w.writeheader()
            for r in results:
                w.writerow(r)
        print(f"\nwrote {args.csv_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
