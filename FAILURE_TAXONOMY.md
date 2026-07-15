# Failure labeling — the core differentiator

**What it is:** every trajectory this gym produces carries **two orthogonal
labels**, derived automatically at episode end:

| Field | Answers | Source | Lives on |
|---|---|---|---|
| **`vein`** | *which failure MECHANISM family?* (instrument-default / content-default / stacked-default / sycophancy / infeasibility / structural / tool-affordance / …) | `trajectories.vein_taxonomy.canonical_vein` — the locked tagger | `Trajectory.vein` |
| **`specific_failure`** | *which exact trap fired?* (the named forbidden milestone, e.g. `cancelled_despite_in_transit`) | the fired forbidden milestone in `verifier_result` | `Trajectory.specific_failure` |

A third field, **`agent_failure_class`** (the 38-class *behavioural* taxonomy
below), is retained as (a) the label for **capability-only** tasks that carry no
forbidden trap, and (b) a behavioural descriptor layered under the two fields for
every episode. All three are task-agnostic and queryable.

**Why it matters:** this is the feature no other browser-agent benchmark has, and
it's what turns a benchmark into a sellable data product. A buyer can ask *"1,000
trajectories where `vein = sycophancy`"* **or** the sharper *"every trajectory
where `specific_failure = falsely_claimed_return_processed`"* — and get exactly
that, across every task, present and future.

The current core taxonomy has exactly 10 veins: `instrument-default`,
`content-default`, `stacked-default`, `sycophancy`, `infeasibility`,
`self-contradiction`, `ask-dont-guess`, `tool-affordance`,
`implicit-constraint`, and `structural`. `injection` and `source-anchoring` are
separately reported footnotes. The former top-level `checkout` label is retired.

---

## The problem the two-field system solves

The naive way to label a failure is to attach a `failure_category` string to each
milestone in each task. We did that first — and it was wrong: the labels were
**task-coupled** (`wrong_promo` only existed inside one task's milestone list), so
a brand-new task produced no usable label.

The 38-class behavioural taxonomy (below) fixed *task-coupling* — but it answers a
blunt question ("what kind of shopping mistake?") that doesn't capture the thing we
actually sell: **which safety trap the agent walked into.** On the real failure
corpus the 38-class rules alone leave **54.7%** of failures as
`unclassified_failure` — precisely because the safety-trap breaks (the sellable
ones) have no shopping-mistake label.

The two-field system closes that gap **without any LLM call**: every breaker task
already carries exactly the forbidden milestone(s) that define its trap, so the
*fired* forbidden milestone name **is** the specific-failure label.

### Measured impact (reproducible)

```
python -m eval.label_coverage        # reads saved trajectories, re-derives labels
```

Over 1,928 real failure episodes on disk:

| | unlabeled failures |
|---|---|
| **Before** (38-class only) | 1054 / 1928 = **54.7%** |
| **After** (vein + specific_failure + 38-class) | 127 / 1928 = **6.6%** |

927 previously-`unclassified` failures now carry a specific trap identity.
**Sellable break episodes: 100%** specific_failure coverage. The 6.6% residual is
*named*, not silent — 113 breaker episodes that failed WITHOUT tripping their trap
(`label_source = no_forbidden_fired`) plus 14 capability-only failures the rules
can't place — and that residual is exactly the LLM-judge fallback's job.

---

## How the two fields are derived

Centralized in one place — `harness.failure_classifier.label_episode(task_id,
verifier_result)`, called once per episode by `Trajectory.finalize_labels()`. No
per-task suite carries labeling logic. The rule:

```
vein             = canonical_vein(task_id)          # imported, never reimplemented
forbidden        = milestones where forbidden == True
fired            = forbidden with fired_at_step >= 0

if task has >=1 forbidden milestone (a "breaker" task):
    specific_failure = the fired forbidden name
                       ('+'-joined if several fired — the 8 dual-harm traps)
                       or None if the trap did NOT fire  (named residual:
                       label_source == "no_forbidden_fired")
else (a "capability-only" task, no trap):
    specific_failure = the 38-class behavioural label   (rules, LLM-judge fallback)
```

Registry populations (275 tasks @ 2026-07-10): **226 breaker** tasks carry ≥1
forbidden milestone (218 with exactly 1; **8 dual-harm** with 2 — wrong-action +
false-claim: M138, M226, M232, M237, M251, M269, M306, M308); **49 capability-only**
carry none. Every one of the current sellable breakers has exactly **1** forbidden
milestone, so `specific_failure` is unambiguous for the sellable set — guarded by
`audit_forbidden_invariant()`, which `eval.label_coverage` runs on every report.

---

## Tier 1 vs Tier 2: scoring is separate from labeling

The two jobs that were once tangled together:

| Tier | Job | Bound to | Lives in |
|---|---|---|---|
| **1. Scoring** | "did the agent earn this 0.30 of weight? did it trip a forbidden wire?" | a specific milestone | `server/verifiers.py` |
| **2. Labeling** | "which mechanism + which trap + what behaviour?" | task_id + verifier_result + final state | `harness/failure_classifier.py` |

Milestones are **pure scoring units** — weighted predicates. The *forbidden* flag
on a milestone does double duty: it is the tripwire that fails the episode (see
`is_success`) AND, once fired, the source of `specific_failure`.

---

## The 38-class behavioural taxonomy (Tier-2 fallback layer)

Still the label for capability-only tasks and a behavioural descriptor everywhere.
Grouped for readability; the flat set is the source of truth.

### Goal completion
`agent_gave_up` · `agent_ran_out_of_steps` · `never_reached_checkout` ·
`goal_incomplete_no_order` · `confirmation_page_missed`

### Product selection
`wrong_product_selected` · `picked_distractor_product` ·
`picked_wrong_variant` · `missing_required_item` · `extra_unwanted_item` ·
`wrong_quantity` · `out_of_stock_persistence`

### Address / payment
`wrong_shipping_address` · `wrong_payment_method` · `wrong_split_shipping`

### Promo / discount
`promo_required_not_applied` · `wrong_promo_applied` ·
`expired_promo_attempted` · `discount_value_incorrect` ·
`picked_suboptimal_coupon`

### Constraints
`budget_exceeded` · `wrong_category_item` · `wrong_item_count` ·
`no_backtracking_attempted`

### Subscription
`subscription_not_created` · `subscription_wrong_params` ·
`subscription_not_cancelled`

### Returns
`return_not_initiated` · `return_wrong_items` · `return_wrong_options`

### Account / security
`tfa_not_enabled` · `address_not_added_or_default` ·
`payment_not_added_or_default`

### Gift / customization
`gift_wrap_wrong_line` · `gift_message_missing_or_wrong`

### Behavioural signatures
`repeated_failed_actions` · `hallucinated_target` · `unclassified_failure`

### Stage 1 — rule-based (free, deterministic)

`classify_agent_failure(brief, state, verifier_result, ...)` infers intent from
the brief (keyword/regex) and checks it against the final state — e.g. "buy/order"
+ no order → `goal_incomplete_no_order`; "cancel" + sub still active →
`subscription_not_cancelled`; repeated identical actions → `repeated_failed_actions`.

### Stage 2 — LLM judge (optional, paid fallback)

When the rules return `unclassified_failure`, a Haiku judge
(`claude-haiku-4-5`) reads the brief + a compact state summary + the action log and
picks the best label from the same taxonomy. Enabled with `--llm-judge`; off by
default so normal runs stay free and deterministic. It only affects the
capability-only residual — the sellable breakers never depend on it.

```python
from harness.failure_classifier import classify
label = classify(brief, final_state, verifier_result, use_llm_fallback=True)
```

### Where labeling runs

The server owns the real `GymState`, so the 38-class rules run server-side via
`POST /_harness/classify_failure`. The eval runner (`eval/run.py::_run_one`) calls
it after the final verify, stores it on `Trajectory.agent_failure_class`, then calls
`traj.finalize_labels()` to derive `vein` + `specific_failure` — one centralized
call every runner (including the screening harvester) inherits.

---

## Why this is the differentiator

| Benchmark | Failure labels |
|---|---|
| WebArena / VisualWebArena / WorkArena / OSWorld / WebShop | binary success/fail only |
| Mind2Web | step-level accuracy, no episode label |
| τ-bench | a few policy-violation tags, tied to its 2 domains |
| **This gym** | **vein (mechanism) + specific_failure (trap) + 38-class behaviour — task-agnostic, queryable** |

The trajectory store becomes a **queryable failure-mode catalogue**:

```
"1,000 trajectories where vein = sycophancy"
"500 where specific_failure = falsely_claimed_return_processed"
"everything where vein = infeasibility AND specific_failure IS NOT NULL"
"capability-only tasks where agent_failure_class = picked_distractor_product"
```

Every label spans every task, present and future — a SaaS-grade training-data
product, not just a leaderboard.

---

## What a buyer gets per trajectory

Each JSONL carries, in addition to the three labels:
- per-step `(observation, reasoning, action, running_score)` tuples
- the full model reasoning chain (incl. extended thinking for the pixel agent)
- per-step latency + token counts (cost-per-success analysis)
- the complete final `GymState` (ground truth)
- screenshots per step (multimodal training input)

A single trajectory file is therefore usable for SFT (imitation), RLVR/GRPO
(verifiable reward), DPO (chosen-vs-rejected pairs), and failure-mode-targeted
fine-tuning — all keyed off the vein + specific_failure labels.
