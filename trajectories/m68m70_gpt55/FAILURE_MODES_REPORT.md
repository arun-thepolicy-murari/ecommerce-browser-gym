# Failure-mode report

- **Task**: `M68/case_of_wine_quantity_creep`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  2/3 (67%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 2})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `eca03108` (seed 0, stalled at step 15, 16 steps)

### `missed:ordered_wine_to_sam`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['ordered_wine_to_sam']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `9b687157` (seed 2, stalled at step 0, 20 steps)
