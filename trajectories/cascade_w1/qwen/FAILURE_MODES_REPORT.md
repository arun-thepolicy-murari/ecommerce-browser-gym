# Failure-mode report

- **Task**: `M139/no_laptop_under_budget`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/3 (33%)

- **dominant failure_class**: `no_backtracking_attempted`  (breakdown: {'no_backtracking_attempted': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `c8b778d4` (seed 0, stalled at step 1, 25 steps)
