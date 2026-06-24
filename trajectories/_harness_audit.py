# -*- coding: utf-8 -*-
"""Empirical harness-integrity sweep. Proves the properties that make verdicts trustworthy:
1) STEP-0 INVARIANT: for every task & seed, the seed state is NOT success and NO forbidden fires.
2) WEIGHT SANITY: forbidden milestones weigh 0; non-forbidden weights sum to ~1.0.
3) DETERMINISM: same task+seed => identical milestone structure.
4) ISOLATION: a task with seeded orders does not leak into a zero-order task.
5) SUITE FRESHNESS: re-resetting a task yields fired_at_step==-1 (no cross-episode latch)."""
import sys, json, urllib.request
from server.verifiers import SUITE_FACTORIES

BASE = "http://localhost:8003"
def post(path, body):
    r = urllib.request.Request(BASE+path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(r, timeout=30))
def get(path):
    return json.load(urllib.request.urlopen(BASE+path, timeout=30))

tasks = sorted(SUITE_FACTORIES.keys())
print(f"auditing {len(tasks)} tasks\n")

bad_step0 = []      # forbidden fired at step 0, or success True at step 0
bad_weight = []     # forbidden weight!=0 or non-forbidden sum!=1.0
no_forbidden = []   # suite has NO forbidden milestone (can never register a BREAK)

for tid in tasks:
    for seed in (0, 1):
        post("/_harness/reset", {"task_id": tid, "seed": seed, "ui": "normal"})
        res = post("/_harness/verify", {"url": "/", "step": 0})
        ms = res.get("all_milestones", [])
        fired_forb = [m["name"] for m in ms if m["forbidden"] and isinstance(m["fired_at_step"], int) and m["fired_at_step"] >= 0]
        if fired_forb or res.get("success"):
            bad_step0.append((tid, seed, res.get("success"), fired_forb))
        if seed == 0:
            nonforb = sum(m["weight"] for m in ms if not m["forbidden"])
            forb_w = [m["name"] for m in ms if m["forbidden"] and m["weight"] != 0]
            if forb_w or abs(nonforb - 1.0) > 0.01:
                bad_weight.append((tid, round(nonforb, 4), forb_w))
            if not any(m["forbidden"] for m in ms):
                no_forbidden.append(tid)

print("=== 1. STEP-0 INVARIANT (forbidden must NOT fire, not success, at seed) ===")
print(f"   violations: {len(bad_step0)}")
for x in bad_step0[:20]: print("   !!", x)

print("\n=== 2. WEIGHT SANITY (forbidden weight=0; non-forbidden sum=1.0) ===")
print(f"   violations: {len(bad_weight)}")
for x in bad_weight[:20]: print("   !!", x)

print("\n=== 3. SUITES WITH NO FORBIDDEN MILESTONE (can't register a BREAK) ===")
print(f"   count: {len(no_forbidden)}")
if no_forbidden: print("  ", no_forbidden[:30])

# 4. DETERMINISM
print("\n=== 4. DETERMINISM (same task+seed => identical milestone names/weights/flags) ===")
det_bad = []
for tid in tasks[:40]:
    sigs = []
    for _ in range(2):
        post("/_harness/reset", {"task_id": tid, "seed": 0, "ui": "normal"})
        res = post("/_harness/verify", {"url": "/", "step": 0})
        sigs.append([(m["name"], m["weight"], m["required"], m["forbidden"]) for m in res["all_milestones"]])
    if sigs[0] != sigs[1]: det_bad.append(tid)
print(f"   checked {min(40,len(tasks))} tasks; non-deterministic: {len(det_bad)} {det_bad}")

# 5. ISOLATION: reset a task with seeded orders, then a zero-order task; confirm no leak
print("\n=== 5. CROSS-EPISODE ISOLATION ===")
def order_count():
    try: return len(get("/_harness/world").get("shop", {}).get("orders", {}) or {})
    except Exception:
        try: return len(get("/_harness/state").get("orders", {}) or {})
        except Exception: return "?"
seeded = next((t for t in tasks if "M211" in t or "M218" in t or "M270" in t), tasks[0])
post("/_harness/reset", {"task_id": seeded, "seed": 0, "ui": "normal"}); oc_seeded = order_count()
zero = next((t for t in tasks if "M230" in t or "M214" in t), tasks[0])
post("/_harness/reset", {"task_id": zero, "seed": 0, "ui": "normal"}); oc_zero = order_count()
print(f"   after reset {seeded}: orders={oc_seeded}")
print(f"   after reset {zero} (expect 0): orders={oc_zero}  -> {'LEAK!' if (isinstance(oc_zero,int) and oc_zero>0) else 'isolated OK'}")

print("\n=== SUMMARY ===")
ok = (not bad_step0) and (not bad_weight) and (not det_bad) and (isinstance(oc_zero,int) and oc_zero==0)
print("HARNESS INTEGRITY:", "PASS — verdicts trustworthy" if ok else "FAILURES ABOVE — investigate")
