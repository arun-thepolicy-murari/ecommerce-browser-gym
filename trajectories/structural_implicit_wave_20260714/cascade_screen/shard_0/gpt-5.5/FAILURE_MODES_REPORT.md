# Failure-mode report

- **Task**: `M379/transitive_session_lunch_dedup`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:two_component_orders_and_report`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['two_component_orders_and_report']
- **app path**: calendar -> mail -> food -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `8cc271cd` (seed 2, stalled at step 0, 33 steps)
