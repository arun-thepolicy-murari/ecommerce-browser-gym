# Failure-mode report

- **Task**: `M24/procurement_puzzle`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 8  ·  **Successes**: 7  ·  **Failures**: 1  (failure rate **12%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:applied_value10+ordered_three_at_valuemart+under_budget`  —  1/8 (12%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['applied_value10', 'ordered_three_at_valuemart', 'under_budget']
- **app path**: shop
- **fact gap (required facts never observed)**: ['market.basket_total']
- **representative episode**: `7ae813f4` (seed 6, stalled at step 0, 19 steps)
