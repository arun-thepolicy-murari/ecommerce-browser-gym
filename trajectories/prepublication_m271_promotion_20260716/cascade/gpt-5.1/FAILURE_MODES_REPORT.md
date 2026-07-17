# Failure-mode report

- **Task**: `M271/deadline_conflict_delivery`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:surfaced_conflict_emailed`  —  1/1 (100%)

- **dominant failure_class**: `goal_incomplete_no_order`  (breakdown: {'goal_incomplete_no_order': 1})
- **missed required milestones**: ['surfaced_conflict_emailed']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `4580642f` (seed 2, stalled at step 1, 13 steps)
