# Failure-mode report

- **Task**: `M20/errand_run`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:replied_gear_total_to_alex`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['replied_gear_total_to_alex']
- **app path**: shop -> mail -> shop -> food -> calendar -> mail
- **fact gap (required facts never observed)**: ['food.eta']
- **representative episode**: `11a9ac29` (seed 1, stalled at step 46, 50 steps)
