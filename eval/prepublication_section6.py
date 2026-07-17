"""Generate the low-cost Section 6 statistical-protocol evidence.

No model calls are made. The script rebuilds seeded worlds in process and reads
the current sellable ledger's retained screening evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from server.apps.calendar.state import make_calendarstate
from server.apps.food.state import make_foodstate
from server.apps.mail.state import make_mailstate
from server.apps.market.state import make_marketstate
from server.apps.world import WorldState
from server.tasks import make_task
from trajectories.vein_taxonomy import canonical_vein


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "trajectories/sellable_breakers_v2.csv"
OUT = ROOT / "trajectories/prepublication_section6_20260715"
APPENDIX = ROOT / "docs/RAW_THREE_SEED_DISTRIBUTIONS.md"
MODELS = ("qwen", "gpt-5.1", "gpt-5.5", "sonnet")
GRID_MODELS = ("gpt-5.1", "gpt-5.5", "sonnet")
TECHNICAL_FIELDS = {
    "seed", "step", "finished", "task_id", "created_at", "received_at",
    "placed_at", "timestamp", "sent_at", "updated_at",
}


def _world(task_id: str, seed: int) -> WorldState:
    """Mirror server.main._reset_inline without mutating the live server."""
    built = make_task(task_id, seed)
    if isinstance(built, WorldState):
        world = built
        if world.mail is None:
            world.mail = make_mailstate(seed)
        if world.food is None:
            world.food = make_foodstate(seed)
        if world.calendar is None:
            world.calendar = make_calendarstate(seed)
        if world.market is None:
            world.market = make_marketstate(seed)
        return world
    return WorldState(
        shop=built,
        mail=make_mailstate(seed),
        food=make_foodstate(seed),
        calendar=make_calendarstate(seed),
        market=make_marketstate(seed),
    )


def _normalize(value: Any, *, technical: bool = False) -> Any:
    if isinstance(value, dict):
        out = {}
        for key in sorted(value):
            if key in {"seed", "step", "finished", "task_id"}:
                continue
            if technical and key in TECHNICAL_FIELDS:
                out[key] = "<normalized>"
            else:
                out[key] = _normalize(value[key], technical=technical)
        return out
    if isinstance(value, list):
        return [_normalize(item, technical=technical) for item in value]
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _diff(a: Any, b: Any, path: str = "$") -> list[dict[str, Any]]:
    if type(a) is not type(b):
        return [{"path": path, "seed_a": a, "seed_b": b}]
    if isinstance(a, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            p = f"{path}.{key}"
            if key not in a:
                out.append({"path": p, "seed_a": "<missing>", "seed_b": b[key]})
            elif key not in b:
                out.append({"path": p, "seed_a": a[key], "seed_b": "<missing>"})
            else:
                out.extend(_diff(a[key], b[key], p))
        return out
    if isinstance(a, list):
        out = []
        for index in range(max(len(a), len(b))):
            p = f"{path}[{index}]"
            if index >= len(a):
                out.append({"path": p, "seed_a": "<missing>", "seed_b": b[index]})
            elif index >= len(b):
                out.append({"path": p, "seed_a": a[index], "seed_b": "<missing>"})
            else:
                out.extend(_diff(a[index], b[index], p))
        return out
    return [] if a == b else [{"path": path, "seed_a": a, "seed_b": b}]


def _canonicalize_entity_maps(value: Any) -> Any:
    """Ignore generated map keys while preserving the entity payload."""
    if isinstance(value, dict):
        if value and all(
            isinstance(item, dict) and item.get("id") == key
            for key, item in value.items()
        ):
            records = []
            for item in value.values():
                record = {
                    key: _canonicalize_entity_maps(val)
                    for key, val in item.items() if key != "id"
                }
                records.append(record)
            return sorted(records, key=lambda item: json.dumps(item, sort_keys=True))
        return {
            key: _canonicalize_entity_maps(val)
            for key, val in sorted(value.items())
        }
    if isinstance(value, list):
        return [_canonicalize_entity_maps(item) for item in value]
    return value


def _without_shared_book_club(value: dict[str, Any]) -> dict[str, Any]:
    """Remove the one global parity fixture, then canonicalize generated IDs."""
    value = deepcopy(value)
    events = value.get("calendar", {}).get("events", {})
    value["calendar"]["events"] = {
        key: event for key, event in events.items()
        if event.get("title") != "Book club"
    }
    return _canonicalize_entity_maps(value)


def build_seed_evidence(rows: list[dict[str, str]]) -> dict[str, Any]:
    tasks = []
    counts: Counter[str] = Counter()
    for row in rows:
        task_id = row["task_id"]
        try:
            raw = [deepcopy(_world(task_id, seed).to_json()) for seed in range(3)]
            norm = [_normalize(item) for item in raw]
            technical = [_normalize(item, technical=True) for item in raw]
            without_parity = [_without_shared_book_club(item) for item in norm]
            hashes = [_digest(item) for item in norm]
            technical_hashes = [_digest(item) for item in technical]
            if len(set(hashes)) == 1:
                classification = "identical scenario repeated for model stochasticity"
            elif len(set(technical_hashes)) == 1:
                classification = "only IDs/timestamps vary"
            else:
                classification = "meaningful scenario-state variation"
            parity_only = (
                classification == "meaningful scenario-state variation"
                and len({_digest(item) for item in without_parity}) == 1
            )
            pair_diffs = {}
            for left, right in ((0, 1), (0, 2), (1, 2)):
                changes = _diff(norm[left], norm[right])
                pair_diffs[f"{left}_vs_{right}"] = {
                    "changed_field_count": len(changes),
                    "sample": changes[:20],
                }
            tasks.append({
                "task_id": task_id,
                "classification": classification,
                "normalized_world_hashes": dict(zip(("0", "1", "2"), hashes)),
                "technical_normalized_hashes": dict(
                    zip(("0", "1", "2"), technical_hashes)
                ),
                "variation_attribution": (
                    "shared calendar parity fixture only"
                    if parity_only else
                    "none" if classification.startswith("identical") else
                    "additional task-specific or non-calendar variation"
                ),
                "field_diffs": pair_diffs,
            })
        except Exception as exc:  # evidence must preserve unknowns
            classification = "unknown"
            tasks.append({
                "task_id": task_id,
                "classification": classification,
                "error": f"{type(exc).__name__}: {exc}",
            })
        counts[classification] += 1
    return {
        "schema_version": 1,
        "generated_from": [
            "server.main._reset_inline",
            "server.tasks.make_task",
            "WorldState.to_json",
            str(LEDGER.relative_to(ROOT)),
        ],
        "normalization": {
            "always_removed": ["task_id", "seed", "step", "finished"],
            "technical_comparison_normalized_fields": sorted(TECHNICAL_FIELDS),
            "hash": "SHA-256 over canonical JSON",
            "classification_rule": (
                "identical if normalized hashes match; IDs/timestamps-only if "
                "technical-normalized hashes match; otherwise meaningful variation"
            ),
        },
        "task_count": len(rows),
        "counts": dict(counts),
        "task_ids_by_classification": {
            label: [t["task_id"] for t in tasks if t["classification"] == label]
            for label in (
                "identical scenario repeated for model stochasticity",
                "meaningful scenario-state variation",
                "only IDs/timestamps vary",
                "unknown",
            )
        },
        "variation_attribution_counts": dict(Counter(
            task.get("variation_attribution", "unknown") for task in tasks
        )),
        "variation_attribution_note": (
            "Seed 1 adds a shared 'Book club' calendar event; seeds 0 and 2 "
            "do not. Generated calendar-event key shifts caused by that insertion "
            "are canonicalized for attribution. No audited sellable has additional "
            "task-specific scenario variation across seeds 0/1/2."
        ),
        "tasks": tasks,
    }


def _parse_grid(cell: str) -> list[tuple[int, int] | None] | None:
    parts = [part.strip() for part in (cell or "").split("·")]
    if len(parts) != 3:
        return None
    result = []
    for part in parts:
        if part in {"", "—", "-"}:
            result.append(None)
            continue
        match = re.fullmatch(r"(\d+)\s*/\s*(\d+)", part)
        if not match:
            return None
        result.append((int(match.group(1)), int(match.group(2))))
    return result


def _mentions(text: str, model: str) -> list[tuple[int, int]]:
    aliases = {
        "qwen": r"qwen(?:-235b)?",
        "gpt-5.1": r"gpt-5\.1",
        "gpt-5.5": r"gpt-5\.5",
        "sonnet": r"sonnet",
    }
    return [
        (int(a), int(b))
        for a, b in re.findall(
            aliases[model] + r"\s+~?(\d+)\s*/\s*(\d+)", text, flags=re.I
        )
    ]


def _cell(row: dict[str, str], model: str) -> dict[str, Any]:
    grid = _parse_grid(row.get("model_grid (5.1·5.5·son)", ""))
    if model in GRID_MODELS and grid is not None:
        value = grid[GRID_MODELS.index(model)]
        if value is None:
            return {"bucket": "not-screened", "source": "model_grid explicit dash"}
        numerator, denominator = value
        if denominator == 3 and 0 <= numerator <= 3:
            return {
                "bucket": f"{numerator}/3",
                "numerator": numerator,
                "denominator": denominator,
                "source": "model_grid",
            }
        return {
            "bucket": "other-denominator",
            "numerator": numerator,
            "denominator": denominator,
            "source": "model_grid",
        }

    text = row.get("models_broken (fail/total)", "")
    values = _mentions(text, model)
    if values:
        numerator, denominator = values[-1]
        bucket = (
            f"{numerator}/3"
            if denominator == 3 and 0 <= numerator <= 3
            else "other-denominator"
        )
        return {
            "bucket": bucket,
            "numerator": numerator,
            "denominator": denominator,
            "source": "models_broken fallback",
        }
    if re.search(
        rf"{re.escape(model)}[^,)]*(?:not screened|not-screened)",
        text,
        flags=re.I,
    ):
        return {"bucket": "not-screened", "source": "explicit text"}
    return {"bucket": "missing", "source": "no parseable retained cell"}


def build_distributions(rows: list[dict[str, str]]) -> dict[str, Any]:
    order = ("0/3", "1/3", "2/3", "3/3", "missing", "not-screened",
             "other-denominator")
    cells = []
    table: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    denominators: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        task_id = row["task_id"]
        vein = canonical_vein(task_id)
        for model in MODELS:
            cell = _cell(row, model)
            cells.append({"task_id": task_id, "vein": vein, "model": model, **cell})
            table[vein][model][cell["bucket"]] += 1
            if "denominator" in cell:
                denominators[model][str(cell["denominator"])] += 1

    distributions = {}
    for vein in sorted(table):
        distributions[vein] = {}
        n = sum(table[vein][MODELS[0]].values())
        for model in MODELS:
            counts = {bucket: table[vein][model][bucket] for bucket in order}
            assert sum(counts.values()) == n
            distributions[vein][model] = {"task_count": n, **counts}

    model_totals = {}
    for model in MODELS:
        counts = Counter(c["bucket"] for c in cells if c["model"] == model)
        assert sum(counts.values()) == len(rows)
        model_totals[model] = {bucket: counts[bucket] for bucket in order}

    return {
        "schema_version": 1,
        "source": str(LEDGER.relative_to(ROOT)),
        "scope": (
            "current N=85 sellable ledger; standard Qwen/GPT-5.1/GPT-5.5/"
            "Sonnet evidence only; Sol, Opus, HY3, and Inkling excluded"
        ),
        "model_versions": {
            "qwen": "qwen/qwen3-vl-235b-a22b-instruct where recorded by standard cascade",
            "gpt-5.1": "gpt-5.1",
            "gpt-5.5": "gpt-5.5",
            "sonnet": "claude-sonnet-4-6 where recorded by standard cascade",
        },
        "bucket_order": list(order),
        "task_count": len(rows),
        "canonical_vein_count": len(distributions),
        "canonical_veins": sorted(distributions),
        "distributions": distributions,
        "model_totals": model_totals,
        "observed_denominators": {
            model: dict(sorted(counts.items())) for model, counts in denominators.items()
        },
        "cells": cells,
        "limitations": [
            "Malformed structured grid cells use only exact retained fractions in models_broken.",
            "Historical denominators other than three are never converted to three-seed bins.",
            "Missing means no parseable retained model-task fraction in the current ledger.",
            "Not-screened requires an explicit dash or explicit retained statement.",
        ],
    }


def write_appendix(raw: dict[str, Any]) -> None:
    buckets = raw["bucket_order"]
    lines = [
        "# Raw three-seed screening distributions",
        "",
        "**Evidence date:** 2026-07-15  ",
        "**Scope:** current 85-row sellable ledger; standard screening track only.",
        "",
        "This appendix excludes the Sol/Opus comparison track and HY3/Inkling "
        "external runs. It does not convert historical 1/1, 2/7, 4/4, or other "
        "non-three-run evidence into three-seed bins. `Missing` means that the "
        "current ledger has no parseable retained model-task fraction; "
        "`not-screened` requires an explicit dash or statement.",
        "",
        "Model identifiers are Qwen "
        "`qwen/qwen3-vl-235b-a22b-instruct` where recorded, `gpt-5.1`, "
        "`gpt-5.5`, and Sonnet `claude-sonnet-4-6` where recorded.",
        "",
        "Each row below has the fixed column order "
        "**0/3 · 1/3 · 2/3 · 3/3 · missing · not-screened · other-denominator**. "
        "Every row sums to that vein's N.",
        "",
        "| Canonical vein (N) | Qwen | GPT-5.1 | GPT-5.5 | Sonnet |",
        "|---|---:|---:|---:|---:|",
    ]
    for vein, model_rows in raw["distributions"].items():
        n = model_rows["qwen"]["task_count"]
        cells = []
        for model in MODELS:
            cells.append(" · ".join(str(model_rows[model][bucket]) for bucket in buckets))
        lines.append(f"| {vein} ({n}) | " + " | ".join(cells) + " |")
    lines.extend([
        "",
        "## Corpus-wide model totals",
        "",
        "| Model | 0/3 | 1/3 | 2/3 | 3/3 | Missing | Not-screened | Other denominator | Total |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for model in MODELS:
        totals = raw["model_totals"][model]
        values = [totals[bucket] for bucket in buckets]
        lines.append(
            f"| {model} | " + " | ".join(map(str, values)) +
            f" | {sum(values)} |"
        )
    lines.extend([
        "",
        "The source precedence is the structured current "
        "`model_grid (5.1·5.5·son)` cell when parseable, followed only by an "
        "exact model fraction in `models_broken (fail/total)`. Malformed prose "
        "is not inferred. Full model-task cells, sources, denominators, and "
        "consistency totals are in "
        "[`raw_distributions.json`](../trajectories/prepublication_section6_20260715/raw_distributions.json).",
        "",
    ])
    APPENDIX.write_text("\n".join(lines))


def main() -> None:
    rows = list(csv.DictReader(LEDGER.open()))
    OUT.mkdir(parents=True, exist_ok=True)
    seed = build_seed_evidence(rows)
    raw = build_distributions(rows)
    (OUT / "seed_variation.json").write_text(
        json.dumps(seed, indent=2, sort_keys=True) + "\n"
    )
    (OUT / "raw_distributions.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n"
    )
    write_appendix(raw)
    print(json.dumps({
        "seed_counts": seed["counts"],
        "raw_model_totals": raw["model_totals"],
        "veins": raw["canonical_vein_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
