# Failure-mode report

- **Task**: `M43/stale_delivery_date`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:reminder_on_live_day`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 3})
- **missed required milestones**: ['reminder_on_live_day']
- **app path**: calendar -> shop -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `01883b44` (seed 0, stalled at step 0, 8 steps)
