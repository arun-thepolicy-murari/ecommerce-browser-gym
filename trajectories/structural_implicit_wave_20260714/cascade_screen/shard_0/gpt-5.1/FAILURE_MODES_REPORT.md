# Failure-mode report

- **Task**: `M379/transitive_session_lunch_dedup`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:two_component_orders_and_report`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['two_component_orders_and_report']
- **app path**: mail -> food -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `71283975` (seed 2, stalled at step 0, 23 steps)
