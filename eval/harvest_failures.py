"""Failure-mode harvester — the deliverable.

Runs a weak agent (default gpt-4o-mini) on a cross-app task K times, then
mines the FAILED trajectories for recurring, statistically-significant
CAUSAL failure modes. Two layers are stored per failure:

  * failure_class           — the broad, reusable universal-taxonomy label
                              (from harness/failure_classifier), e.g.
                              wrong_source_of_truth.
  * failure_mode_signature  — the crystallized recurring chain, built from
                              SEMANTIC STATE DELTAS (normalized actions + app
                              transitions + score-plateau point + facts
                              observed vs required + final-state mismatch).

Clustering is by SIGNATURE (not by class); each cluster reports its dominant
class. A cluster recurring at >= threshold is a real, sellable failure mode.

Usage:
    # run + analyze (needs OPENAI_API_KEY in env, gym server running):
    python -m eval.harvest_failures --tasks M2/order_then_track_via_email \
        --k 12 --server http://localhost:8011

    # re-analyze already-collected trajectories (no API, instant):
    python -m eval.harvest_failures --tasks M2/order_then_track_via_email \
        --analyze-only --traj-dir trajectories/harvest

Output:
    <out>/_report.json + FAILURE_MODES_REPORT.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from server.tasks import REQUIRED_FACTS


# --------------------------------------------------------------------------- #
# Signature building (semantic state deltas)
# --------------------------------------------------------------------------- #

def _app_of(url: str) -> str:
    """Which app a URL belongs to."""
    if "/mail" in url:
        return "mail"
    if "/food" in url:
        return "food"
    if "/calendar" in url:
        return "calendar"
    return "shop"


def _app_path(steps: list[dict]) -> list[str]:
    """The sequence of apps the agent visited, with consecutive repeats
    collapsed — e.g. shop -> mail -> shop. This is where cross-app memory
    loss happens (at the seams)."""
    path: list[str] = []
    for s in steps:
        app = _app_of(s.get("url_after", ""))
        if not path or path[-1] != app:
            path.append(app)
    return path


def _plateau_step(steps: list[dict]) -> int:
    """The step index after which running_score stopped increasing — the
    stall point where the agent effectively went wrong. -1 if it never
    scored."""
    best = -1.0
    plateau = -1
    for s in steps:
        sc = float(s.get("running_score", 0.0))
        if sc > best + 1e-9:
            best = sc
            plateau = s.get("step_idx", plateau)
    return plateau


def _observed_facts(steps: list[dict]) -> dict[str, Any]:
    """Union of every fact the environment showed across the trajectory."""
    facts: dict[str, Any] = {}
    for s in steps:
        for k, v in (s.get("facts_visible_or_created") or {}).items():
            if v is not None:
                facts[k] = v
    return facts


def _missed_required(traj: dict) -> list[str]:
    """Required milestones that never fired (the final-state mismatch)."""
    vr = traj.get("verifier_result") or {}
    out = []
    for m in vr.get("all_milestones", []):
        if m.get("required") and m.get("fired_at_step", -1) < 0:
            out.append(m["name"])
    return sorted(out)


# Human-readable chain labels mapped from the missed-required set per task.
# These turn the structural signature into the sellable "the agent broke
# THIS way" phrase.
def _chain_label(task_id: str, missed: list[str], fact_gap: list[str],
                 app_path: list[str], branch_free: bool | None = None,
                 alex_available: bool | None = None) -> str:
    m = set(missed)
    if task_id == "M2/order_then_track_via_email":
        if "mouse_ordered" in m:
            return "abandoned_or_wrong_purchase__no_confirmation_to_act_on"
        if "opened_confirmation_email" in m:
            return "ordered_but_never_opened_confirmation_email"
        if "tracking_viewed_for_correct_order" in m:
            return "opened_email_but_tracked_wrong_or_no_order"
        return "m2_unexpected_partial"
    if task_id == "M3/dinner_then_receipt":
        if "food_order_placed" in m:
            return "never_placed_food_order"
        if "opened_receipt_email" in m:
            return "ordered_but_never_opened_receipt"
        return "m3_unexpected_partial"
    if task_id == "M4/order_then_reply_total":
        if "mouse_ordered" in m:
            return "never_ordered_the_mouse"
        if "opened_confirmation_email" in m:
            return "ordered_but_never_opened_confirmation"
        if "replied_to_confirmation" in m:
            return "ordered_read_email_but_never_replied"
        if "reply_states_correct_charged_total" in m:
            return "replied_with_wrong_total_not_charged_amount"
        return "m4_unexpected_partial"
    if task_id == "M5/cheaper_mouse_from_deals":
        if "ordered_cheaper_ergonomic_mouse" in m:
            # fact-gap disambiguates the two distinct modes: if no mouse id was
            # ever observed, the agent NEVER completed an order (checkout
            # fumble); otherwise it DID order, but the wrong (decoy) mouse.
            if "shop.ordered_mouse_id" in fact_gap:
                return "compared_deals_then_failed_to_complete_order"
            return "ordered_the_wrong_decoy_mouse"
        return "m5_unexpected_partial"
    if task_id == "M6/reorder_bigger_order":
        if "reordered_bigger_orders_instock_items" in m:
            return "wrong_or_no_reorder_of_bigger_order"
        if "replied_listing_reordered_items" in m:
            return "reordered_but_never_replied_with_list"
        return "m6_unexpected_partial"
    if task_id == "M7/dinner_and_host_gift":
        if "food_order_under_35" in m:
            return "food_over_budget_or_not_ordered"
        if "bought_qualifying_book" in m:
            return "bought_disqualified_or_no_book"
        if "replied_to_alex_with_eta_and_book" in m:
            return "did_both_but_reply_missing_eta_or_book"
        return "m7_unexpected_partial"
    if task_id == "M8/spending_audit_branch":
        if "correct_branch_made_no_new_purchase" in m \
                and "replied_cancel_to_most_expensive_order" in m:
            return "took_treat_yourself_branch_instead_of_cancel"
        if "correct_branch_made_no_new_purchase" in m:
            return "made_a_purchase_wrong_branch"
        if "replied_cancel_to_most_expensive_order" in m:
            return "no_cancel_reply_or_wrong_order"
        return "m8_unexpected_partial"
    if task_id == "M9/calendar_gated_dinner":
        food = "food_action_matches_calendar" in m
        cal = "calendar_event_matches_branch" in m
        email = "emailed_alex_correct_branch" in m
        if branch_free is False:
            # BUSY seed: correct branch is don't-order + propose Thursday.
            if food:
                return "ordered_dinner_despite_busy_calendar"
            if email:
                return "busy_no_order_but_missing_thursday_proposal"
            if cal:
                return "added_event_despite_busy_calendar"
            return "m9_busy_unexpected_partial"
        # FREE seed: correct branch is order + event + confirm.
        if food and email:
            return "took_busy_branch_despite_free_calendar"
        if food:
            return "free_but_never_ordered_dinner"
        if cal:
            return "ordered_but_forgot_calendar_event"
        if email:
            return "did_actions_but_no_or_wrong_confirmation_email"
        return "m9_free_unexpected_partial"
    if task_id == "M10/dinner_source_conflict":
        food = "food_action_matches_sources" in m
        email = "emailed_alex_correct_branch" in m
        if alex_available is False:
            # CONFLICT seed: calendar says free but Alex can't make it. Correct
            # branch = don't order + reply to reschedule.
            if food and email:
                return "ignored_email_ordered_and_confirmed_despite_conflict"
            if food:
                return "ordered_despite_alex_unavailable"
            if email:
                return "skipped_order_but_no_reschedule_reply"
            return "m10_conflict_unexpected_partial"
        # NO-CONFLICT seed: correct branch = order + confirm.
        if food:
            return "available_but_never_ordered"
        if email:
            return "ordered_but_no_confirmation_reply"
        return "m10_noconflict_unexpected_partial"
    if task_id == "M11/cancel_unshipped_over_100":
        missed_some = "cancelled_all_qualifying" in m      # didn't cancel all it should
        hit_extra = "cancelled_only_qualifying" in m       # cancelled something it shouldn't
        if missed_some and hit_extra:
            return "missed_a_qualifying_and_cancelled_a_trap"
        if missed_some:
            return "missed_a_qualifying_cancellation"       # lost track over 8 items
        if hit_extra:
            return "cancelled_a_shipped_or_cheap_order"      # skipped a filter condition
        return "m11_unexpected_partial"
    if task_id == "M13/order_cleanup_audit":
        missed_some = "cancelled_all_required" in m       # skipped a real cancel
        cancelled_wrong = "cancelled_only_required" in m  # cancelled a skip
        if missed_some and cancelled_wrong:
            return "missed_a_required_and_cancelled_a_skip"
        if cancelled_wrong:
            # The headline trap: cancelled a charged<=$50 item (read the
            # subtotal not the charged total), or the gift, or a shipped order.
            return "cancelled_on_subtotal_or_gift_not_charged"
        if missed_some:
            return "missed_a_required_cancellation_over_14_items"
        return "m13_unexpected_partial"
    if task_id == "M12/bulk_add_dense_grid":
        missed_some = "added_all_qualifying" in m       # skipped a qualifying item
        added_wrong = "added_only_qualifying" in m      # added a non-qualifying item
        if missed_some and added_wrong:
            return "missed_a_qualifying_and_added_a_wrong_item"
        if missed_some:
            return "missed_a_qualifying_add_in_the_crowd"
        if added_wrong:
            return "added_a_non_qualifying_item_misclick"
        return "m12_unexpected_partial"
    return "missed:" + "+".join(missed) if missed else "no_required_missed"


def build_signature(traj: dict) -> dict[str, Any]:
    """Build the two-layer failure record for one failed trajectory."""
    task_id = traj.get("task_id", "")
    steps = traj.get("steps", [])
    missed = _missed_required(traj)
    app_path = _app_path(steps)
    plateau = _plateau_step(steps)
    observed = _observed_facts(steps)
    required = list(REQUIRED_FACTS.get(task_id, []))
    fact_gap = sorted([f for f in required if f not in observed])
    # For gated M9, the correct branch hinges on the calendar. Prefer the value
    # the agent actually observed; fall back to the seed parity (even=free).
    branch_free = observed.get("calendar.evening_free")
    if branch_free is None and task_id == "M9/calendar_gated_dinner":
        branch_free = (int(traj.get("seed", 0)) % 2 == 0)
    # M10's branch hinges on Alex's email (even seeds benign, odd = conflict).
    alex_available = observed.get("mail.alex_available")
    if alex_available is None and task_id == "M10/dinner_source_conflict":
        alex_available = (int(traj.get("seed", 0)) % 2 == 0)
    chain = _chain_label(task_id, missed, fact_gap, app_path, branch_free,
                         alex_available)

    # The clustering key: two failures are "the same mode" iff this matches.
    signature_key = "|".join([
        chain,
        "miss=" + "+".join(missed),
        "gap=" + ",".join(fact_gap),
    ])

    return {
        "failure_class": traj.get("agent_failure_class"),       # broad layer
        "vein": traj.get("vein"),                               # mechanism family
        "specific_failure": traj.get("specific_failure"),       # fired trap (sellable)
        "failure_mode_signature": chain,                        # crystallized layer
        "signature_key": signature_key,
        "missed_required": missed,
        "app_path": app_path,
        "plateau_step": plateau,
        "facts_observed": observed,
        "facts_required": required,
        "fact_gap": fact_gap,
        "n_steps": len(steps),
        "score": (traj.get("verifier_result") or {}).get("score", 0.0),
        "episode_id": traj.get("episode_id"),
        "seed": traj.get("seed"),
    }


# --------------------------------------------------------------------------- #
# Clustering + significance
# --------------------------------------------------------------------------- #

def cluster(signatures: list[dict], total_runs: int,
            min_rate: float, min_n: int) -> dict[str, Any]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for sig in signatures:
        groups[sig["signature_key"]].append(sig)

    clusters = []
    for key, members in groups.items():
        rep = members[0]
        classes = Counter(s["failure_class"] for s in members)
        dominant_class = classes.most_common(1)[0][0] if classes else None
        n = len(members)
        rate = n / total_runs if total_runs else 0.0
        clusters.append({
            "failure_mode_signature": rep["failure_mode_signature"],
            "signature_key": key,
            "count": n,
            "rate": round(rate, 3),
            "significant": (rate >= min_rate and n >= min_n),
            "dominant_failure_class": dominant_class,
            "failure_class_breakdown": dict(classes),
            "missed_required": rep["missed_required"],
            "app_path": rep["app_path"],
            "fact_gap": rep["fact_gap"],
            "representative": {
                "episode_id": rep["episode_id"],
                "seed": rep["seed"],
                "plateau_step": rep["plateau_step"],
                "n_steps": rep["n_steps"],
            },
        })
    clusters.sort(key=lambda c: -c["count"])
    return {"clusters": clusters}


# --------------------------------------------------------------------------- #
# Run phase
# --------------------------------------------------------------------------- #

async def _run_k(task_id: str, k: int, *, agent: str, model: str | None,
                 server_url: str, traj_dir: Path, ui_variant: str,
                 seeds: list[int] | None = None) -> list[dict]:
    from eval.run import _run_one
    out: list[dict] = []
    run_seeds = seeds if seeds is not None else list(range(k))
    for n, seed in enumerate(run_seeds):
        print(f"  [{n + 1}/{len(run_seeds)}] {agent} on {task_id} "
              f"seed={seed} ui={ui_variant}")
        traj = await _run_one(
            agent_kind=agent, task_id=task_id, seed=seed,
            server_url=server_url, headless=True, record_video=False,
            out_traj_dir=traj_dir, out_screens_dir=Path("screenshots/harvest"),
            llm_model=model, ui=ui_variant,
        )
        out.append(traj.to_json())
    return out


def _load_trajectories(traj_dir: Path, task_id: str) -> list[dict]:
    safe = task_id.replace("/", "_")
    trajs = []
    for p in sorted(traj_dir.glob(f"{safe}__*.jsonl")):
        try:
            trajs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"  skip {p.name}: {e}")
    return trajs


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def _write_reports(task_id: str, trajs: list[dict], report: dict,
                   out_dir: Path, model: str, ui_variant: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(trajs)
    failures = [t for t in trajs if not (t.get("verifier_result") or {}).get("success")]
    successes = total - len(failures)

    payload = {
        "task_id": task_id,
        "model": model,
        "ui_variant": ui_variant,
        "total_runs": total,
        "successes": successes,
        "failures": len(failures),
        "failure_rate": round(len(failures) / total, 3) if total else 0.0,
        "clusters": report["clusters"],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out_dir / "_report.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Failure-mode report",
        "",
        f"- **Task**: `{task_id}`",
        f"- **Model**: `{model}`  ·  **UI variant**: `{ui_variant}`",
        f"- **Runs**: {total}  ·  **Successes**: {successes}  ·  "
        f"**Failures**: {len(failures)}  "
        f"(failure rate **{payload['failure_rate']:.0%}**)",
        "",
        "Each failure carries TWO layers: a broad `failure_class` (reusable "
        "taxonomy label) and a crystallized `failure_mode_signature` (the "
        "recurring causal chain). Clusters are grouped by SIGNATURE.",
        "",
        "## Recurring failure modes (by signature, most frequent first)",
        "",
    ]
    if not report["clusters"]:
        lines.append("_No failures to cluster._")
    for c in report["clusters"]:
        flag = "  ⭐ STATISTICALLY SIGNIFICANT" if c["significant"] else ""
        lines += [
            f"### `{c['failure_mode_signature']}`  —  "
            f"{c['count']}/{total} ({c['rate']:.0%}){flag}",
            "",
            f"- **dominant failure_class**: `{c['dominant_failure_class']}`  "
            f"(breakdown: {c['failure_class_breakdown']})",
            f"- **missed required milestones**: "
            f"{c['missed_required'] or 'none'}",
            f"- **app path**: {' -> '.join(c['app_path']) or '(none)'}",
            f"- **fact gap (required facts never observed)**: "
            f"{c['fact_gap'] or 'none'}",
            f"- **representative episode**: `{c['representative']['episode_id']}` "
            f"(seed {c['representative']['seed']}, "
            f"stalled at step {c['representative']['plateau_step']}, "
            f"{c['representative']['n_steps']} steps)",
            "",
        ]
    (out_dir / "FAILURE_MODES_REPORT.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"\nReports written to {out_dir}/_report.json + "
          f"{out_dir}/FAILURE_MODES_REPORT.md")


def _print_summary(task_id: str, report: dict, total: int) -> None:
    print("\n" + "=" * 80)
    print(f"FAILURE MODES - {task_id}  ({total} runs)")
    print("-" * 80)
    for c in report["clusters"]:
        flag = " *** SIGNIFICANT" if c["significant"] else ""
        print(f"  {c['count']:>3}/{total} ({c['rate']:>4.0%})  "
              f"{c['failure_mode_signature']}  "
              f"[{c['dominant_failure_class']}]{flag}")
    print("=" * 80)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default="M2/order_then_track_via_email",
                    help="comma-separated cross-app task ids")
    ap.add_argument("--k", type=int, default=12, help="runs per task")
    ap.add_argument("--seeds", default=None,
                    help="explicit comma-separated seeds (overrides --k); e.g. "
                         "'1,3,5,7' to harvest only the busy M9 branch")
    ap.add_argument("--agent", default="openai",
                    choices=["openai", "openai_pixel", "openai_coord", "llm",
                             "pixel", "pixel_coord", "qwen"],
                    help="weak agent to harvest (default openai = gpt-4o-mini "
                         "DOM; openai_pixel = gpt-4o-mini SoM/pixel; "
                         "openai_coord = GPT raw-coordinate (no SoM); "
                         "pixel_coord = Anthropic raw-coordinate, no SoM)")
    ap.add_argument("--model", default=None,
                    help="model id (default gpt-4o-mini for openai)")
    ap.add_argument("--server", default="http://localhost:8000")
    ap.add_argument("--ui", default="normal", help="UI variant tag (metadata)")
    ap.add_argument("--analyze-only", action="store_true",
                    help="skip running; analyze trajectories already in --traj-dir")
    ap.add_argument("--traj-dir", default="trajectories/harvest")
    ap.add_argument("--out", default="trajectories/harvest")
    ap.add_argument("--min-rate", type=float, default=0.5,
                    help="significance threshold: cluster rate")
    ap.add_argument("--min-n", type=int, default=3,
                    help="significance threshold: cluster count")
    args = ap.parse_args()

    traj_dir = Path(args.traj_dir)
    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    seeds = ([int(s) for s in args.seeds.split(",") if s.strip()]
             if args.seeds else None)

    for task_id in tasks:
        n_runs = len(seeds) if seeds is not None else args.k
        print(f"\n### Harvesting {task_id} (n={n_runs}, agent={args.agent}, "
              f"seeds={seeds if seeds is not None else f'0..{args.k - 1}'})")
        if args.analyze_only:
            trajs = _load_trajectories(traj_dir, task_id)
            print(f"  loaded {len(trajs)} trajectories from {traj_dir}")
        else:
            trajs = asyncio.run(_run_k(
                task_id, args.k, agent=args.agent, model=args.model,
                server_url=args.server, traj_dir=traj_dir, ui_variant=args.ui,
                seeds=seeds))

        total = len(trajs)
        failures = [t for t in trajs
                    if not (t.get("verifier_result") or {}).get("success")]
        signatures = [build_signature(t) for t in failures]
        report = cluster(signatures, total_runs=total,
                         min_rate=args.min_rate, min_n=args.min_n)
        _print_summary(task_id, report, total)
        model_label = args.model or ("gpt-4o-mini" if args.agent == "openai"
                                     else "default")
        _write_reports(task_id, trajs, report, Path(args.out),
                       model_label, args.ui)


if __name__ == "__main__":
    main()
