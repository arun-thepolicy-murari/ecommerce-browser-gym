# Failure-mode report

- **Task**: `M51/oos_no_substitute`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:considered_requested_item`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['considered_requested_item']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `f28dffb3` (seed 0, stalled at step 0, 8 steps)
