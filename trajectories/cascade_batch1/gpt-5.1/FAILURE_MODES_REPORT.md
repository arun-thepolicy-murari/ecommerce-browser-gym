# Failure-mode report

- **Task**: `M62/three_gift_split`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_all_three_correctly`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 3})
- **missed required milestones**: ['ordered_all_three_correctly']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `b70ee19c` (seed 0, stalled at step 0, 10 steps)
