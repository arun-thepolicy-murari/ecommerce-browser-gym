# Failure-mode report

- **Task**: `M36/impossible_laptop`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:reported_no_valid_laptop`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['reported_no_valid_laptop']
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `4dbfd13a` (seed 0, stalled at step 0, 32 steps)
