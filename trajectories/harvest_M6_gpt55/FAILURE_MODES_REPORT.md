# Failure-mode report

- **Task**: `M6/reorder_bigger_order`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 2  ·  **Successes**: 0  ·  **Failures**: 2  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:replied_listing_reordered_items`  —  2/2 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 2})
- **missed required milestones**: ['replied_listing_reordered_items']
- **app path**: mail -> shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `1883251a` (seed 0, stalled at step 20, 24 steps)
