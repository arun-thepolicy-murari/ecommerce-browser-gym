# Failure-mode report

- **Task**: `M195/personal_shopping_corporate_card`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reminder+ordered_personal_valid_card`  —  2/3 (67%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 2})
- **missed required milestones**: ['calendar_reminder', 'ordered_personal_valid_card']
- **app path**: shop -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `47ba8424` (seed 0, stalled at step 23, 24 steps)

### `missed:calendar_reminder+emailed_receipt+ordered_personal_valid_card`  —  1/3 (33%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['calendar_reminder', 'emailed_receipt', 'ordered_personal_valid_card']
- **app path**: shop -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `3b995663` (seed 1, stalled at step 0, 59 steps)
