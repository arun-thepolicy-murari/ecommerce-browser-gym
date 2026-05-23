# Failure-mode report

- **Task**: `M5/cheaper_mouse_from_deals`
- **Model**: `gpt-4o-mini`  ·  **UI variant**: `normal`
- **Runs**: 10  ·  **Successes**: 7  ·  **Failures**: 3  (failure rate **30%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `compared_deals_then_failed_to_complete_order`  —  3/10 (30%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `goal_incomplete_no_order`  (breakdown: {'goal_incomplete_no_order': 3})
- **missed required milestones**: ['ordered_cheaper_ergonomic_mouse']
- **app path**: mail -> shop -> mail -> shop
- **fact gap (required facts never observed)**: ['shop.ordered_mouse_id']
- **representative episode**: `1e9bf53c` (seed 2, stalled at step 3, 17 steps)
