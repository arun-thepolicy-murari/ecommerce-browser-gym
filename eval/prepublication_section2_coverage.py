"""Build Section 2A four-part coverage matrix for the exact 85 sellables.

Outputs:
  trajectories/prepublication_section2_20260716/four_part_coverage.json
"""

from __future__ import annotations

import ast
import csv
import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "trajectories" / "sellable_breakers_v2.csv"
INVENTORY = ROOT / "trajectories" / "task_verifier_inventory.json"
OUT_DIR = ROOT / "trajectories" / "prepublication_section2_20260716"
OUT_JSON = OUT_DIR / "four_part_coverage.json"

SECTION3_SEED = (
    "tests/test_section3_reward_hacking.py"
    "::test_preexisting_state_cannot_succeed_or_fire_forbidden"
)
SECTION3_LATCH = (
    "tests/test_section3_reward_hacking.py"
    "::test_forbidden_latch_survives_repair"
)
NEW_HARM = {
    "M271/deadline_conflict_delivery",
    "M272/surprise_gift_timing",
    "M307/value_anchoring_false_perunit_claim_sycophancy",
    "M312/usbc_cable_wont_fit_lightning_phone",
}

# Holds / footnotes documented outside the 85 active ledger.
MEMBERSHIP_NOTES = {
    "active_sellable_source": "trajectories/sellable_breakers_v2.csv",
    "active_count": 85,
    "held_out_of_ledger": [
        {
            "task_id": "M56/gift_errand",
            "note": "Release hold — not in active 85; see docs/history/audits/M56_RELEASE_HOLD_2026-07-15.md",
        }
    ],
    "footnote_classes_within_85": [
        "injection (e.g. M59)",
        "source-anchoring (e.g. M43)",
    ],
}


def _sellable_ids() -> list[str]:
    with LEDGER.open(newline="", encoding="utf-8") as handle:
        return [row["task_id"] for row in csv.DictReader(handle)]


def _load_funcs() -> list[dict]:
    out: list[dict] = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        src = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            end = getattr(node, "end_lineno", node.lineno)
            body = ast.get_source_segment(src, node) or ""
            out.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "name": node.name,
                    "lineno": node.lineno,
                    "body": body,
                }
            )
    return out


def _num(tid: str) -> int | None:
    short = tid.split("/", 1)[0]
    return int(short[1:]) if short.startswith("M") and short[1:].isdigit() else None


def _belongs(fn: dict, tid: str) -> bool:
    n = _num(tid)
    short = tid.split("/", 1)[0]
    name, body = fn["name"], fn["body"]
    if n is not None and re.match(rf"^test_m{n}_", name):
        return True
    if n is not None and re.match(rf"^test_m{n}_m\d+", name):
        return True
    # Combined helpers that list multiple task ids in one body
    if tid in body or f'"{short}/' in body or f"'{short}/" in body:
        if n is not None and re.match(r"^test_m\d+_", name) and not re.match(
            rf"^test_m{n}_", name
        ):
            # allow multi-id helpers like test_m271_m272_...
            if re.match(rf"^test_m{n}_m", name) or f"m{n}_m" in name:
                return True
            if tid in body:
                return True
            return False
        return True
    if "m271_m272" in name and tid.startswith(("M271/", "M272/")):
        return True
    return False


SEED_NAME = re.compile(
    r"(env_truth|premise_is|seed_|seeded|is_oos|cart_has|is_genuinely|"
    r"live_tracking|forbidden_silent_at_start|items_seeded|four_part)",
    re.I,
)
POS_NAME = re.compile(
    r"(succeeds|succeed_|scores_one|full_path|positive|gold|correct_path|"
    r"verify_and_decline|check_and_decline|neither_order_ok|"
    r"abstain|flag_to_user|view_and_ask|paypal_succeeds|truthful|"
    r"_ok_|no_mutation_ok|safe_note_ok|four_part)",
    re.I,
)
FORB_NAME = re.compile(
    r"(fails|break|forbidden|harm|wrong_|emailing_|blind_return|"
    r"silent_substitution|named_forbidden|latch_survives)",
    re.I,
)
DONOTH_NAME = re.compile(
    r"(do_nothing|nothing_done|nothing_ordered|never_acted|untouched|four_part)",
    re.I,
)
POS_BODY = re.compile(
    r'assert\s+(?:res(?:_\w+)?|_?probe\(\)|sim\._probe\(\))\["success"\]\s+is\s+True'
    r'|assert\s+sim\._probe\(\)\["success"\]\s+is\s+True'
    r'|score.*==\s*1\.0',
    re.I,
)
FORB_BODY = re.compile(
    r"in\s+_fired\(|fired_forbidden|_fired_forbidden|is_a_break|vetoes|"
    r"assert\s+fired",
    re.I,
)


def _classify(fn: dict) -> set[str]:
    parts: set[str] = set()
    name, body = fn["name"], fn["body"]
    if SEED_NAME.search(name) or "forbidden_false" in body or "not in _fired(res0)" in body:
        parts.add("seed_state")
    if POS_NAME.search(name) or POS_BODY.search(body):
        parts.add("positive_path")
    if FORB_NAME.search(name) or FORB_BODY.search(body):
        if not (DONOTH_NAME.search(name) and "forbidden" not in name.lower()
                and "break" not in name.lower() and not FORB_BODY.search(body)):
            parts.add("forbidden_path")
    if DONOTH_NAME.search(name) or "nothing_done" in name or "do_nothing" in name:
        parts.add("do_nothing")
    if "forbidden_silent_and_do_nothing" in name:
        parts.update({"seed_state", "forbidden_path", "do_nothing"})
    if "nothing_done_not_success" in name or "nothing_ordered_not_success" in name:
        parts.add("do_nothing")
    if "four_part" in name or "seed_positive_forbidden_do_nothing" in name:
        parts.update({"seed_state", "positive_path", "forbidden_path", "do_nothing"})
    if "named_forbidden" in name:
        parts.update({"seed_state", "positive_path", "forbidden_path", "do_nothing"})
    return parts


def build_matrix() -> dict:
    sellable = _sellable_ids()
    assert len(sellable) == 85, len(sellable)
    inv = {t["task_id"]: t for t in json.loads(INVENTORY.read_text())["tasks"]}
    funcs = _load_funcs()

    rows = []
    for tid in sellable:
        matched = []
        seen: set[str] = set()
        for fn in funcs:
            if not _belongs(fn, tid):
                continue
            key = f"{fn['file']}::{fn['name']}"
            if key in seen:
                continue
            seen.add(key)
            matched.append(fn)

        evidence = {p: [] for p in ("seed_state", "positive_path", "forbidden_path", "do_nothing")}
        for fn in matched:
            for part in _classify(fn):
                evidence[part].append(f"{fn['file']}::{fn['name']}")

        # Universal sellable seed/do-nothing pytest from Section 3
        evidence["seed_state"].append(SECTION3_SEED)
        evidence["do_nothing"].append(
            SECTION3_SEED + " + inventory seed_audit noop_incomplete"
        )
        if tid in NEW_HARM:
            evidence["forbidden_path"].append(SECTION3_LATCH)

        sa = inv[tid]["seed_audit"]
        runtime = {
            "forbidden_false_at_step0_all_seeds": all(
                x["forbidden_false_at_step0"] for x in sa
            ),
            "noop_incomplete_all_seeds": all(
                x["noop_incomplete"] and not x["noop_success"] for x in sa
            ),
        }
        present = {p: bool(evidence[p]) for p in evidence}
        # Prefer runtime confirmation for seed/do-nothing
        if runtime["forbidden_false_at_step0_all_seeds"]:
            present["seed_state"] = True
        if runtime["noop_incomplete_all_seeds"]:
            present["do_nothing"] = True

        missing = [p for p, ok in present.items() if not ok]
        rows.append(
            {
                "task_id": tid,
                "parts": {
                    p: {"present": present[p], "evidence": evidence[p][:10]}
                    for p in evidence
                },
                "runtime_seed_audit": runtime,
                "oracle_status": inv[tid].get("oracle", {}).get("status"),
                "focused_test_count": len(matched),
                "focused_tests": [f"{f['file']}::{f['name']}" for f in matched[:25]],
                "complete_four_part": not missing,
                "missing": missing,
                "release_status": inv[tid].get("release_status"),
            }
        )

    n_complete = sum(1 for r in rows if r["complete_four_part"])
    missing_by_part = {
        p: [r["task_id"] for r in rows if p in r["missing"]]
        for p in ("seed_state", "positive_path", "forbidden_path", "do_nothing")
    }
    return {
        "schema_version": 1,
        "date": str(date.today()),
        "method": (
            "Exact 85 from sellable_breakers_v2.csv. Per-task pytest attribution "
            "via AST + name/body classification; Section 3 parametric seed/noop; "
            "inventory seed_audit runtime confirmation; additive "
            "tests/test_section2_four_part_gaps.py for prior missing cells."
        ),
        "membership": MEMBERSHIP_NOTES,
        "summary": {
            "n_sellable": len(rows),
            "n_complete_four_part": n_complete,
            "n_incomplete": len(rows) - n_complete,
            "missing_by_part_counts": {k: len(v) for k, v in missing_by_part.items()},
            "incomplete_task_ids": [r["task_id"] for r in rows if not r["complete_four_part"]],
            "missing_by_part": missing_by_part,
        },
        "tasks": rows,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_matrix()
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    s = payload["summary"]
    print(
        f"four-part coverage: {s['n_complete_four_part']}/{s['n_sellable']} complete; "
        f"incomplete={s['incomplete_task_ids']}"
    )
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
