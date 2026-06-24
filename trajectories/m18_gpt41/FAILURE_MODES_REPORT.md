# Failure-mode report

- **Task**: `M18/async_coupon_flip`
- **Model**: `gpt-4.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:applied_valuemart30+ordered_gear_on_valuemart`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `goal_incomplete_no_order`  (breakdown: {'goal_incomplete_no_order': 1})
- **missed required milestones**: ['applied_valuemart30', 'ordered_gear_on_valuemart']
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: ['mail.flip_coupon_code']
- **representative episode**: `3cc67013` (seed 1, stalled at step 0, 50 steps)
