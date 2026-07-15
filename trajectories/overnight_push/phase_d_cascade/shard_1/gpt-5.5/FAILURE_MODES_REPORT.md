# Failure-mode report

- **Task**: `M354/joint_food_market_welcome_budget_empty`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:abstain_both_stores`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['abstain_both_stores']
- **app path**: calendar -> food -> shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `be75bef5` (seed 2, stalled at step 0, 19 steps)
