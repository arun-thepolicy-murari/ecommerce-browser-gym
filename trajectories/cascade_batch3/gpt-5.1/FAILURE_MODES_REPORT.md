# Failure-mode report

- **Task**: `M70/mixed_basket_two_redirects`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_with_both_gifts_redirected`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 3})
- **missed required milestones**: ['ordered_with_both_gifts_redirected']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `a7efa4b6` (seed 0, stalled at step 0, 22 steps)
