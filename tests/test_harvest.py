"""Pure-logic tests for the failure-mode harvester (eval/harvest_failures).

Synthetic trajectory dicts -> signatures -> clusters. No browser, no API.
This pins the signature builder + clustering — the heart of the deliverable.
"""

from __future__ import annotations

from eval.harvest_failures import (
    build_signature, cluster, _app_path, _plateau_step,
)


def _ms(name: str, required: bool, fired: bool) -> dict:
    return {"name": name, "required": required,
            "fired_at_step": (1 if fired else -1)}


def _traj(*, success: bool, failure_class, steps, all_milestones,
          episode_id="e1", seed=0,
          task_id="M2/order_then_track_via_email") -> dict:
    return {
        "task_id": task_id, "episode_id": episode_id, "seed": seed,
        "agent_failure_class": failure_class,
        "steps": steps,
        "verifier_result": {
            "success": success, "score": 1.0 if success else 0.0,
            "all_milestones": all_milestones,
        },
    }


M2_NONE_FIRED = [
    _ms("mouse_ordered", True, False),
    _ms("confirmation_email_delivered", False, False),
    _ms("opened_confirmation_email", True, False),
    _ms("tracking_viewed_for_correct_order", True, False),
]


def test_app_path_collapses_consecutive_apps():
    steps = [
        {"url_after": "/", "running_score": 0.0},
        {"url_after": "/product/x", "running_score": 0.0},
        {"url_after": "/mail", "running_score": 0.0},
        {"url_after": "/mail/message/em_1", "running_score": 0.0},
        {"url_after": "/account/orders/X/track", "running_score": 0.0},
    ]
    assert _app_path(steps) == ["shop", "mail", "shop"]


def test_plateau_is_last_score_increase():
    steps = [
        {"step_idx": 0, "running_score": 0.0},
        {"step_idx": 1, "running_score": 0.30},
        {"step_idx": 2, "running_score": 0.30},
        {"step_idx": 3, "running_score": 0.30},
    ]
    assert _plateau_step(steps) == 1


def test_m2_never_ordered_signature_and_fact_gap():
    t = _traj(
        success=False, failure_class="repeated_failed_actions",
        steps=[{"step_idx": 0, "url_after": "/", "running_score": 0.0,
                "facts_visible_or_created": {}}],
        all_milestones=M2_NONE_FIRED,
    )
    sig = build_signature(t)
    assert sig["failure_mode_signature"] == \
        "abandoned_or_wrong_purchase__no_confirmation_to_act_on"
    assert sig["failure_class"] == "repeated_failed_actions"          # two layers
    assert set(sig["fact_gap"]) == {"shop.order_id", "mail.tracking_url"}


def test_m2_ordered_but_email_unopened_signature_no_fact_gap():
    ms = [
        _ms("mouse_ordered", True, True),
        _ms("confirmation_email_delivered", False, True),
        _ms("opened_confirmation_email", True, False),
        _ms("tracking_viewed_for_correct_order", True, False),
    ]
    t = _traj(
        success=False,
        failure_class="premature_finish_without_verification",
        steps=[{"step_idx": 2, "url_after": "/order/X", "running_score": 0.45,
                "facts_visible_or_created": {
                    "shop.order_id": "ORD-1",
                    "mail.tracking_url": "/account/orders/ORD-1/track"}}],
        all_milestones=ms,
    )
    sig = build_signature(t)
    assert sig["failure_mode_signature"] == \
        "ordered_but_never_opened_confirmation_email"
    # The facts WERE on screen (just not acted on) -> no gap, but the
    # required milestone still missed: that distinction is the whole point.
    assert sig["fact_gap"] == []
    assert "opened_confirmation_email" in sig["missed_required"]


def test_clustering_groups_by_signature_and_flags_significant():
    def none_fired(eid):
        return build_signature(_traj(
            success=False, failure_class="repeated_failed_actions",
            steps=[{"step_idx": 0, "url_after": "/", "running_score": 0.0,
                    "facts_visible_or_created": {}}],
            all_milestones=M2_NONE_FIRED, episode_id=eid))

    sigs = [none_fired("a"), none_fired("b"), none_fired("c")]
    rep = cluster(sigs, total_runs=4, min_rate=0.5, min_n=2)
    assert len(rep["clusters"]) == 1
    c = rep["clusters"][0]
    assert c["count"] == 3
    assert c["rate"] == 0.75
    assert c["significant"] is True
    assert c["dominant_failure_class"] == "repeated_failed_actions"
