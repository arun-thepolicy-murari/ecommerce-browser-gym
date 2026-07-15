# Failure-mode report

- **Task**: `M195/personal_shopping_corporate_card`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_personal_valid_card`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['ordered_personal_valid_card']
- **app path**: shop -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `0a95749e` (seed 2, stalled at step 56, 57 steps)
