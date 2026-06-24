# Failure-mode report

- **Task**: `M20/errand_run`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_gear_valuemart`  —  2/3 (67%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1, 'never_reached_checkout': 1})
- **missed required milestones**: ['ordered_gear_valuemart']
- **app path**: shop -> food -> calendar -> shop -> mail -> shop -> mail
- **fact gap (required facts never observed)**: ['food.eta']
- **representative episode**: `462ec50e` (seed 0, stalled at step 49, 50 steps)
