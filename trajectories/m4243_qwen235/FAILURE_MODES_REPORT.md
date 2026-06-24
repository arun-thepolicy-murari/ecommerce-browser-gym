# Failure-mode report

- **Task**: `M43/stale_delivery_date`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:reminder_on_live_day`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 2, 'repeated_failed_actions': 1})
- **missed required milestones**: ['reminder_on_live_day']
- **app path**: shop -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `6fe901d9` (seed 0, stalled at step 0, 10 steps)
