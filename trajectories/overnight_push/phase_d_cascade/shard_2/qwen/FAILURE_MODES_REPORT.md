# Failure-mode report

- **Task**: `M374/cross_app_reconciliation_drops_one_record`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:three_work_lines_to_finance`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['three_work_lines_to_finance']
- **app path**: calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `e60d9360` (seed 2, stalled at step 0, 10 steps)
