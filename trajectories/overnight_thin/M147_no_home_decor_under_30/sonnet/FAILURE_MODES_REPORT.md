# Failure-mode report

- **Task**: `M147/no_home_decor_under_30`
- **Model**: `claude-sonnet-4-6`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/3 (33%)

- **dominant failure_class**: `no_backtracking_attempted`  (breakdown: {'no_backtracking_attempted': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `125d22e4` (seed 2, stalled at step 5, 32 steps)
