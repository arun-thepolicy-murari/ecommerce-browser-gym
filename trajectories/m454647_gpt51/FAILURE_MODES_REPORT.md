# Failure-mode report

- **Task**: `M47/phantom_duplicate`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `0980c4b7` (seed 0, stalled at step 1, 19 steps)
