# Failure-mode report

- **Task**: `M141/no_history_book_under_18`
- **Model**: `claude-opus-4-8`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `no_backtracking_attempted`  (breakdown: {'no_backtracking_attempted': 1})
- **missed required milestones**: none
- **app path**: shop -> mail -> shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `ca4ea50e` (seed 2, stalled at step 1, 25 steps)
