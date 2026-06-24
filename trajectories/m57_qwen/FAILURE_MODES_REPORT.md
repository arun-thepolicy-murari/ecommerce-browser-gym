# Failure-mode report

- **Task**: `M57/birthday_errand`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_gift_to_mom`  —  2/3 (67%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 2})
- **missed required milestones**: ['ordered_gift_to_mom']
- **app path**: shop -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `7ef5f279` (seed 1, stalled at step 0, 22 steps)
