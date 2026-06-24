# Failure-mode report

- **Task**: `M204/valuemart_delivery_threshold`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:reported_delivery_fee_charged+valuemart_order_with_coupon`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 3})
- **missed required milestones**: ['reported_delivery_fee_charged', 'valuemart_order_with_coupon']
- **app path**: shop -> mail -> shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `d563678e` (seed 0, stalled at step 0, 18 steps)
