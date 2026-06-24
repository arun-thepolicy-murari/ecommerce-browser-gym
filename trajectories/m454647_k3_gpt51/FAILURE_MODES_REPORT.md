# Failure-mode report

- **Task**: `M47/phantom_duplicate`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  2/3 (67%)

- **dominant failure_class**: `return_wrong_options`  (breakdown: {'return_wrong_options': 1, 'repeated_failed_actions': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `9a58d1b8` (seed 0, stalled at step 1, 13 steps)
