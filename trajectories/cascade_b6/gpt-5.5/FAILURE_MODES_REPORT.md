# Failure-mode report

- **Task**: `M79/shipto_plus_sneaked_addon`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 2, 'unclassified_failure': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `3e313579` (seed 0, stalled at step 13, 14 steps)
