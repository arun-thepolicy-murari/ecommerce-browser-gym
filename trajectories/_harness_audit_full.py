# -*- coding: utf-8 -*-
"""FULL harness-integrity sweep — Phase 0.2 gate artifact.

Runs the four integrity checks the plan requires across ALL 234 tasks (not a 40-task
sample), against a live server at BASE. Emits a JSON summary to stdout's tail and to
--out so the audit report can quote exact numbers.

Checks (gate = 0 violations, all four):
  1. STEP-0 INVARIANT   for every task & seed the seed state is NOT success and NO
                        forbidden milestone has already fired.
  2. WEIGHT SANITY      forbidden milestones weigh 0; non-forbidden weights sum ~1.0.
  3. DETERMINISM        same task+seed => identical milestone structure across resets.
  4. ISOLATION          reset(T) is history-independent: the world after
                        reset(RICH)->reset(T) is identical to reset(T)->reset(T).
                        Prior-episode state leaking through reset would break this.

Informational (not a hard gate, but reported): suites with NO forbidden milestone can
never register a BREAK.
"""
import sys, json, argparse, urllib.request
from harness.auth import harness_headers
from server.verifiers import SUITE_FACTORIES

BASE = "http://localhost:8003"
SEEDS = (0, 1, 2)


def post(path, body):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json", **harness_headers()},
                               method="POST")
    return json.load(urllib.request.urlopen(r, timeout=60))


def get(path):
    r = urllib.request.Request(BASE + path, headers=harness_headers())
    return json.load(urllib.request.urlopen(r, timeout=60))


def reset(tid, seed):
    return post("/_harness/reset", {"task_id": tid, "seed": seed, "ui": "normal"})


def verify_step0():
    return post("/_harness/verify", {"url": "/", "step": 0})


def milestone_sig(ms):
    """Structural signature — insensitive to fired_at_step (which is dynamic)."""
    return [(m["name"], m["weight"], m["required"], m["forbidden"]) for m in ms]


def canon_world(w):
    w = dict(w)
    w.pop("step", None)      # step is 0 after reset but pop defensively
    return json.dumps(w, sort_keys=True, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="trajectories/_harness_audit_full.json")
    ap.add_argument("--rich", default="M13/order_cleanup_audit",
                    help="heavily-seeded task used as the isolation contaminator")
    args = ap.parse_args()

    tasks = sorted(SUITE_FACTORIES.keys())
    print(f"auditing {len(tasks)} tasks x seeds {SEEDS} against {BASE}\n", flush=True)

    bad_step0 = []      # (tid, seed, success, [forbidden names already fired])
    bad_weight = []     # (tid, seed, nonforb_sum, [forbidden names with weight!=0])
    no_forbidden = []   # tid with zero forbidden milestones (can't register BREAK)
    det_bad = []        # (tid, seed) whose two resets disagree structurally
    iso_bad = []        # (tid) whose world differs by predecessor

    # sanity: confirm the rich contaminator exists
    rich = args.rich if args.rich in SUITE_FACTORIES else tasks[0]

    for i, tid in enumerate(tasks):
        forb_seen_any = False
        for seed in SEEDS:
            reset(tid, seed)
            res = verify_step0()
            ms = res.get("all_milestones", [])
            # (1) step-0 invariant
            fired_forb = [m["name"] for m in ms
                          if m["forbidden"] and isinstance(m["fired_at_step"], int) and m["fired_at_step"] >= 0]
            if fired_forb or res.get("success"):
                bad_step0.append((tid, seed, res.get("success"), fired_forb))
            # (2) weight sanity (per seed)
            nonforb = sum(m["weight"] for m in ms if not m["forbidden"])
            forb_w = [m["name"] for m in ms if m["forbidden"] and m["weight"] != 0]
            if forb_w or abs(nonforb - 1.0) > 0.01:
                bad_weight.append((tid, seed, round(nonforb, 4), forb_w))
            if any(m["forbidden"] for m in ms):
                forb_seen_any = True
        if not forb_seen_any:
            no_forbidden.append(tid)

        # (3) determinism — two resets at seed 0 must give identical structure
        reset(tid, 0); s1 = milestone_sig(verify_step0().get("all_milestones", []))
        reset(tid, 0); s2 = milestone_sig(verify_step0().get("all_milestones", []))
        if s1 != s2:
            det_bad.append((tid, 0))

        # (4) isolation — reset(T) must not depend on prior episode
        reset(tid, 0)          # clean predecessor = T itself
        reset(tid, 0); w_clean = canon_world(get("/_harness/world"))
        reset(rich, 0)         # dirty predecessor = richest-state task
        reset(tid, 0); w_dirty = canon_world(get("/_harness/world"))
        if w_clean != w_dirty:
            iso_bad.append(tid)

        if (i + 1) % 40 == 0:
            print(f"  ...{i+1}/{len(tasks)} tasks swept", flush=True)

    print("\n=== 1. STEP-0 INVARIANT (forbidden must NOT fire, not success, at seed) ===")
    print(f"   violations: {len(bad_step0)}")
    for x in bad_step0[:30]:
        print("   !!", x)

    print("\n=== 2. WEIGHT SANITY (forbidden weight=0; non-forbidden sum=1.0) ===")
    print(f"   violations: {len(bad_weight)}")
    for x in bad_weight[:30]:
        print("   !!", x)

    print("\n=== 3. DETERMINISM (same task+seed => identical milestone structure) ===")
    print(f"   checked {len(tasks)} tasks; non-deterministic: {len(det_bad)}")
    for x in det_bad[:30]:
        print("   !!", x)

    print("\n=== 4. CROSS-EPISODE ISOLATION (reset history-independence) ===")
    print(f"   contaminator: {rich}; leaks: {len(iso_bad)}")
    for x in iso_bad[:30]:
        print("   !!", x)

    print("\n=== INFO: SUITES WITH NO FORBIDDEN MILESTONE (can't register a BREAK) ===")
    print(f"   count: {len(no_forbidden)}")
    if no_forbidden:
        print("  ", no_forbidden[:40])

    summary = {
        "n_tasks": len(tasks),
        "seeds": list(SEEDS),
        "contaminator": rich,
        "violations": {
            "step0_invariant": len(bad_step0),
            "weight_sanity": len(bad_weight),
            "determinism": len(det_bad),
            "isolation": len(iso_bad),
        },
        "detail": {
            "step0_invariant": bad_step0,
            "weight_sanity": bad_weight,
            "determinism": det_bad,
            "isolation": iso_bad,
        },
        "info": {"suites_no_forbidden": no_forbidden},
    }
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)

    total = sum(summary["violations"].values())
    print("\n=== SUMMARY ===")
    print(json.dumps(summary["violations"]))
    print(f"suites_no_forbidden(info): {len(no_forbidden)}")
    print("HARNESS INTEGRITY:", "PASS — 0 violations across all 4 checks" if total == 0
          else f"FAIL — {total} violations, investigate above")
    print(f"[wrote {args.out}]")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
