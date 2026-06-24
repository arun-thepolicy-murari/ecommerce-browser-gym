# Failure-mode report

- **Task**: `M55/split_shipping`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_both_gift_to_mom`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 2, 'unclassified_failure': 1})
- **missed required milestones**: ['ordered_both_gift_to_mom']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `6ad1dafc` (seed 0, stalled at step 0, 15 steps)
