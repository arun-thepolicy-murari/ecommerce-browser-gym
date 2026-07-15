# Failure-mode report

- **Task**: `M195/personal_shopping_corporate_card`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reminder+emailed_receipt+ordered_personal_valid_card`  —  1/1 (100%)

- **dominant failure_class**: `goal_incomplete_no_order`  (breakdown: {'goal_incomplete_no_order': 1})
- **missed required milestones**: ['calendar_reminder', 'emailed_receipt', 'ordered_personal_valid_card']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `7efc8102` (seed 2, stalled at step 0, 28 steps)
