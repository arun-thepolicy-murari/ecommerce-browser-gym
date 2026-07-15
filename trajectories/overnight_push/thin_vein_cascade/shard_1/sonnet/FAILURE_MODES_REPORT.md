# Failure-mode report

- **Task**: `M349/four_meals_for_five_people`
- **Model**: `claude-sonnet-4-6`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:emailed_user_cardinality_conflict`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['emailed_user_cardinality_conflict']
- **app path**: calendar -> food -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `dd8f8f01` (seed 2, stalled at step 0, 17 steps)
