# Failure-mode report

- **Task**: `M55/split_shipping`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_both_gift_to_mom`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['ordered_both_gift_to_mom']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `18f491a2` (seed 2, stalled at step 0, 14 steps)
