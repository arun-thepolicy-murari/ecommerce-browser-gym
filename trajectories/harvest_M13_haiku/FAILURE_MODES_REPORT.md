# Failure-mode report

- **Task**: `M13/order_cleanup_audit`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 6  ·  **Successes**: 4  ·  **Failures**: 2  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed_a_required_cancellation_over_14_items`  —  2/6 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: ['cancelled_all_required']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `2ae5afaa` (seed 0, stalled at step 0, 49 steps)
