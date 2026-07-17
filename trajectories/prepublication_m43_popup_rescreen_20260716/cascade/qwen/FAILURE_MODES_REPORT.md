# Failure-mode report

- **Task**: `M43/stale_delivery_date`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:reminder_on_live_day`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['reminder_on_live_day']
- **app path**: shop -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `9afe8327` (seed 2, stalled at step 0, 8 steps)
