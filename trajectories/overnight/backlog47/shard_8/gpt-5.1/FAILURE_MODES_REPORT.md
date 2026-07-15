# Failure-mode report

- **Task**: `M191/office_kit_card_trap`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reminder+finance_told_exact_total+ordered_kit_valid_card+self_told_exact_total`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['calendar_reminder', 'finance_told_exact_total', 'ordered_kit_valid_card', 'self_told_exact_total']
- **app path**: shop -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `00a27927` (seed 2, stalled at step 0, 54 steps)
