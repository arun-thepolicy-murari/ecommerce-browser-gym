# Failure-mode report

- **Task**: `M18/async_coupon_flip`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:applied_valuemart30+ordered_gear_on_valuemart`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['applied_valuemart30', 'ordered_gear_on_valuemart']
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: ['mail.flip_coupon_code']
- **representative episode**: `99ae75ce` (seed 0, stalled at step 0, 29 steps)

### `missed:applied_valuemart30`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['applied_valuemart30']
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: ['mail.flip_coupon_code']
- **representative episode**: `f8e8302d` (seed 2, stalled at step 38, 39 steps)
