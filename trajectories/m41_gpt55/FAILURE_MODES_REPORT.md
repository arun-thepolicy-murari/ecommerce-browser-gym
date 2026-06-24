# Failure-mode report

- **Task**: `M41/ambiguous_return`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `return_wrong_options`  (breakdown: {'return_wrong_options': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `8c18fc49` (seed 0, stalled at step 1, 12 steps)
