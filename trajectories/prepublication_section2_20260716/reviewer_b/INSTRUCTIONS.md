# Reviewer B — Independent verifier review (Section 2C)

**Role:** Reviewer B derives expected success / harm terminal states from the
**task prompt** (and, if needed, what a normal user can see in the live apps),
**blind to existing verifier code**.

**This folder is usable by a human Reviewer B.** An optional
`independent_ai_reviewer_b` first fill exists and is **explicitly labeled AI —
not human**. Do **not** claim human Reviewer B completion until a human fills
`scoring_sheet_template.csv` (or an equivalent sheet).

## Blindness rules

1. **Allowed before writing expectations**
   - **`BLIND_PROMPTS_AND_SEED_STATES.md`** (preferred) — prompts + plain-language
     initial seed worlds for all 85 sellables; **no** verifier logic
   - `PROMPTS_ONLY.md` / `prompts_only.json` (prompts only; older thinner pack)
   - Optionally: interact with a fresh task instance as a user would (browser UI
     only) — no `/_harness/*`, no debugger dumps of suite predicates
2. **Forbidden until after your sheet is written**
   - **`VERIFIER_LOGIC_REFERENCE.md`** (same folder — post-blind only)
   - `server/verifiers.py` / suite factories
   - `agents/oracle_agent.py` solvers
   - Focused pytest bodies that encode gold/harm mutations
   - `docs/BENCHMARK_VALIDITY_AND_VERIFIER_REFERENCE.md` milestone listings
3. **After** you finish the sheet, you may open verifier materials for the
   reconciliation pass described below.

## What to write (per task)

Use `scoring_sheet_template.csv` (`reviewer_type=human_reviewer_b`):

| Field | Meaning |
|---|---|
| `expected_success_terminal` | What durable world state + messages count as success |
| `expected_harm_terminal` | What wrong commit should fail / count as the break |
| `key_facts_agent_must_check` | Facts that must be visible via normal browsing |
| `ambiguity_notes` | Underspecification / ask-don't-guess notes |
| `confidence_1_to_5` | Your confidence in the above |

Write in your own words. Prefer observable end states over implementation jargon.

## Scope

- **P1 initial-report scope (protocol):** every headline example + stratified
  sample across veins/archetypes is the minimum for the report.
- **P2 full release:** this packet covers the **exact 85** active sellables in
  `trajectories/sellable_breakers_v2.csv` (M56 held out of ledger — not in this
  85). Prefer completing all 85 for release readiness.

## Reconciliation (after blindness ends)

1. Compare your sheet to:
   - sellable ledger `expected_correct_behavior` / `what_the_agent_does_wrong`
   - **`VERIFIER_LOGIC_REFERENCE.md`** (same folder; post-blind)
   - inventory `required_milestones` / `forbidden_milestones`
     (`trajectories/task_verifier_inventory.json`)
2. Log every disagreement in `RECONCILIATION_LOG.md` (append rows).
3. Resolve explicitly: (a) Reviewer B revises expectation, (b) verifier/test fix
   if a genuine scoring bug, or (c) document intentional design with rationale.
4. **Do not mass-change verifiers** from a first-pass disagreement list.

## AI first fill (optional progress only)

| Artifact | Role |
|---|---|
| `independent_ai_reviewer_b_scores.{json,csv}` | Coarse prompt-heuristic fill |
| `comparison_ai_b_vs_verifier.json` | Post-hoc theme flags + curated notes |

`human_reviewer_b_complete` remains **false** until a human finishes.
