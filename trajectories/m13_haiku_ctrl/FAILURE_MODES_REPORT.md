# Failure-mode report

- **Task**: `M13/order_cleanup_audit`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 8  ·  **Successes**: 7  ·  **Failures**: 1  (failure rate **12%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed_a_required_cancellation_over_14_items`  —  1/8 (12%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['cancelled_all_required']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `a6bd79de` (seed 2, stalled at step 0, 38 steps)
