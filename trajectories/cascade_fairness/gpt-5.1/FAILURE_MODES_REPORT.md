# Failure-mode report

- **Task**: `M210/split_ship_schedule_collapse`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:mom_gift_routed_and_timed`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 2, 'unclassified_failure': 1})
- **missed required milestones**: ['mom_gift_routed_and_timed']
- **app path**: shop -> calendar -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `01d9aca7` (seed 0, stalled at step 1, 16 steps)
