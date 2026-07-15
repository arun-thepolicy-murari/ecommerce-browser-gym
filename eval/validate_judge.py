"""Phase-4 (4.3) — validate the Haiku LLM-judge fallback on the capability-only
population (the 49 tasks with no forbidden trap, where specific_failure falls
back to the 38-class behavioural label and, when the rules punt, to this judge).

Two things this checks, and one it deliberately does NOT:

  FUNCTIONAL (offline, runs here): force the judge on real capability-only
  failures (real brief + real action log + real verifier_result) and confirm it
  (a) always returns an IN-TAXONOMY label and (b) is decisive (rarely punts to
  unclassified_failure). This proves the harness is wired and the model behaves.

  ACCURACY / CALIBRATION (NOT measured offline): the judge keys heavily off the
  final GymState (orders/subscriptions/returns as typed objects). Saved
  trajectories only persist a COUNT-summary snapshot, so an offline judge sees a
  degraded object-state and collapses toward goal-completion defaults. Measured
  agreement with the rules on reconstructed state (~10%) is a STATE-DEGRADATION
  ARTIFACT, not a judge-quality number — do not report it as accuracy.

  The faithful accuracy check is a small LIVE run (see bottom): run N>=30
  capability-only tasks to genuine failure with --llm-judge on, so the judge sees
  the TRUE final state, then compare to the rule label. n~30 => 95% CI ~+/-18pp.

Usage:  .venv/bin/python -m eval.validate_judge          # functional check, n=30
"""
from __future__ import annotations

import glob
import json
import random

import server.tasks as T
import server.verifiers as V
from harness.failure_classifier import llm_classify_agent_failure, FAILURE_TAXONOMY

N = 30
SEED = 7


def _capability_only_shorts():
    return {t.split("/")[0] for t in T.TASKS
            if not any(m.forbidden for m in V.build_suite(t).milestones)}


def _full(short):
    for k in T.TASKS:
        if k.split("/")[0] == short:
            return k
    return None


def _sample():
    caps = _capability_only_shorts()
    bytask = {}
    for p in (glob.glob("trajectories/**/*.jsonl", recursive=True) +
              glob.glob("trajectories/**/*.json", recursive=True)):
        if "__pycache__" in p:
            continue
        try:
            d = json.load(open(p))
        except Exception:
            continue
        for r in (d if isinstance(d, list) else [d]):
            if not isinstance(r, dict):
                continue
            tid, vr = r.get("task_id", ""), r.get("verifier_result")
            s = tid.split("/")[0]
            if (s in caps and isinstance(vr, dict) and not vr.get("success")
                    and r.get("task_brief") and r.get("steps") and s not in bytask):
                bytask[s] = (tid, r["task_brief"], vr, r["steps"])
    out = list(bytask.values())
    random.Random(SEED).shuffle(out)
    return out[:N]


def main():
    sample = _sample()
    valid = specific = 0
    dist = {}
    for tid, brief, vr, steps in sample:
        k = tid if tid in T.TASKS else _full(tid.split("/")[0])
        if not k:
            continue
        state = T.TASKS[k](0)
        state.action_log = [{"kind": st.get("action_kind"),
                             "args": st.get("action_args", {})} for st in steps]
        try:
            j = llm_classify_agent_failure(brief, state, vr, model="claude-haiku-4-5")
        except Exception as e:
            j = f"ERR:{type(e).__name__}"
        inx = j in FAILURE_TAXONOMY
        valid += inx
        specific += (inx and j != "unclassified_failure")
        dist[j] = dist.get(j, 0) + 1

    n = len(sample)
    print(f"=== 4.3 FUNCTIONAL judge validation, capability-only (n={n}) ===")
    print(f"  in-taxonomy validity:        {valid}/{n} = {100*valid/max(n,1):.0f}%")
    print(f"  decisive (non-unclassified): {specific}/{n} = {100*specific/max(n,1):.0f}%")
    print(f"  judge label distribution:    {dict(sorted(dist.items(), key=lambda kv: -kv[1]))}")
    print("\n  ACCURACY is NOT measured here (offline state is degraded; see module")
    print("  docstring). For the faithful calibration number, run the LIVE check:")
    print("    python -m eval.run --agent pixel --model claude-sonnet-4-6 \\")
    print("        --tasks <30 capability-only ids> --seeds 0 --headless --no-video --llm-judge")
    print("  then compare Trajectory.agent_failure_class rule-vs-judge. n~30 => CI ~+/-18pp.")


if __name__ == "__main__":
    main()
