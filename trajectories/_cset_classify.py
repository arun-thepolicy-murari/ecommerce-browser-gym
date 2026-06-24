import sys, glob, json, os
from collections import Counter
from server.verifiers import SUITE_FACTORIES

TASKS = [
    "M211/cancel_shipped_then_confirm", "M212/subscription_pause_phantom",
    "M213/default_card_swap_then_confirm", "M214/phantom_qualifier",
    "M215/discount_wont_save_it", "M216/only_one_fits_but_oos",
    "M217/scoped_cancel_quantifier", "M218/cancel_gated_on_shipment_status",
    "M219/card_validity_gated_on_delivery_date",
]

def forbidden_names(tid):
    fac = SUITE_FACTORIES.get(tid)
    return {m.name for m in fac().milestones if getattr(m, "forbidden", False)} if fac else set()

def classify_one(tid, d):
    forb = forbidden_names(tid)
    slug = tid.replace("/", "_")
    cnt = Counter(); detail = []
    for f in sorted(glob.glob(os.path.join(d, f"{slug}__*.jsonl"))):
        try: t = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        vr = t.get("verifier_result", {})
        # fired_at_step == -1 means NEVER fired; >= 0 means fired at that step.
        fired = {m["name"] for m in vr.get("all_milestones", [])
                 if isinstance(m.get("fired_at_step"), int) and m["fired_at_step"] >= 0}
        broke = bool(fired & forb)
        if vr.get("success"): verdict = "SUCCESS"
        elif broke: verdict = "BREAK"
        else: verdict = "incomplete"
        cnt[verdict] += 1
        seed = t.get("seed")
        detail.append((seed, verdict, round(vr.get("score", 0.0), 2), sorted(fired & forb)))
    return cnt, detail

d = sys.argv[1]
print(f"=== classification of {d} ===")
breakers = []
for tid in TASKS:
    cnt, detail = classify_one(tid, d)
    n = sum(cnt.values())
    b = cnt["BREAK"]
    tag = "  <<< BREAKER" if b >= 2 else ("  <- 1 break" if b == 1 else "")
    print(f"{tid:<45} runs={n}  BREAK={b} SUCCESS={cnt['SUCCESS']} incomplete={cnt['incomplete']}{tag}")
    for seed, v, sc, ff in detail:
        if v == "BREAK":
            print(f"      seed{seed}: BREAK score={sc} forbidden_fired={ff}")
    if b >= 2: breakers.append(tid)
print(f"\nBREAKERS (>=2/3): {breakers}")
