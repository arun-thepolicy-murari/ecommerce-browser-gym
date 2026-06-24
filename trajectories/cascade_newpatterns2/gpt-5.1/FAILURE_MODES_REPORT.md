# Failure-mode report

- **Task**: `M210/split_ship_schedule_collapse`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:mom_gift_routed_and_timed`  —  2/3 (67%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1, 'unclassified_failure': 1})
- **missed required milestones**: ['mom_gift_routed_and_timed']
- **app path**: shop -> calendar -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `c76a61e4` (seed 0, stalled at step 7, 20 steps)
