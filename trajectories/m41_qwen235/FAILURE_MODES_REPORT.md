# Failure-mode report

- **Task**: `M41/ambiguous_return`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:viewed_order_history`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['viewed_order_history']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `48aeafc0` (seed 1, stalled at step 0, 7 steps)

### `no_required_missed`  —  1/3 (33%)

- **dominant failure_class**: `return_wrong_options`  (breakdown: {'return_wrong_options': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `8bb7df47` (seed 2, stalled at step 1, 93 steps)
