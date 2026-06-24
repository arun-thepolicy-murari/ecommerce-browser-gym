# Failure-mode report

- **Task**: `M42/budget_cap`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_both_under_cap`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'goal_incomplete_no_order': 1, 'repeated_failed_actions': 2})
- **missed required milestones**: ['ordered_both_under_cap']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `389b1ce4` (seed 0, stalled at step 0, 20 steps)
