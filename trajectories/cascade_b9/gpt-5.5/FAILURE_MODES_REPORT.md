# Failure-mode report

- **Task**: `M105/false_double_charge`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:verified_order_history`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 3})
- **missed required milestones**: ['verified_order_history']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `ba6c1a10` (seed 0, stalled at step 0, 1 steps)
