# Failure-mode report

- **Task**: `M17/cross_retailer_cheaper`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:applied_value10_coupon+ordered_monitor_on_valuemart`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `promo_required_not_applied`  (breakdown: {'promo_required_not_applied': 1})
- **missed required milestones**: ['applied_value10_coupon', 'ordered_monitor_on_valuemart']
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `541e5c0f` (seed 2, stalled at step 0, 18 steps)
