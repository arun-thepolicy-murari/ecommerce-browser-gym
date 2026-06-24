# Failure-mode report

- **Task**: `M58/cancel_mealkit`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:cancelled_mealkit_sub`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['cancelled_mealkit_sub']
- **app path**: shop -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `b9a6c3f8` (seed 1, stalled at step 0, 38 steps)
