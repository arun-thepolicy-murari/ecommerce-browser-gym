import csv
from collections import Counter
from pathlib import Path

from trajectories.vein_taxonomy import (
    ALLOWED_CANONICAL_VEINS,
    CORE_VEINS,
    DEFAULT_VEIN_BY_SHORT_ID,
    FOOTNOTE_VEINS,
    canonical_vein,
)


ROOT = Path(__file__).resolve().parents[1]
SELLABLE = ROOT / "trajectories" / "sellable_breakers_v2.csv"
AUDITED_SPLIT = ROOT / "trajectories" / "checkout_instrument_content_split.csv"


def _sellable_rows():
    with SELLABLE.open(newline="") as fh:
        return list(csv.DictReader(fh))


def test_audited_default_split_is_the_canonical_mapping():
    with AUDITED_SPLIT.open(newline="") as fh:
        audited = {
            row["task_id"].split("/", 1)[0]:
            row["exclusive_category"].lower()
            for row in csv.DictReader(fh)
        }

    assert audited == DEFAULT_VEIN_BY_SHORT_ID
    assert len(audited) == 42
    assert Counter(audited.values()) == {
        "instrument-default": 9,
        "content-default": 15,
        "stacked-default": 18,
    }
    assert {
        canonical_vein(row["task_id"])
        for row in _sellable_rows()
        if row["task_id"].split("/", 1)[0] in audited
    } == set(audited.values())
    for row in _sellable_rows():
        short = row["task_id"].split("/", 1)[0]
        if short in audited:
            assert canonical_vein(row["task_id"]) == audited[short]


def test_current_sellable_distribution_uses_only_allowed_canonical_labels():
    rows = _sellable_rows()
    labels = [canonical_vein(row["task_id"]) for row in rows]
    counts = Counter(labels)

    assert len(CORE_VEINS) == 10
    assert len(rows) == 86
    assert set(labels) <= ALLOWED_CANONICAL_VEINS
    assert counts["checkout"] == 0
    assert sum(counts[vein] for vein in CORE_VEINS) == 84
    assert sum(counts[vein] for vein in FOOTNOTE_VEINS) == 2
    assert {vein: counts[vein] for vein in CORE_VEINS} == {
        "instrument-default": 9,
        "content-default": 15,
        "stacked-default": 18,
        "sycophancy": 15,
        "infeasibility": 5,
        "self-contradiction": 5,
        "ask-dont-guess": 5,
        "tool-affordance": 5,
        "implicit-constraint": 4,
        "structural": 3,
    }
    assert {vein: counts[vein] for vein in FOOTNOTE_VEINS} == {
        "injection": 1,
        "source-anchoring": 1,
    }
