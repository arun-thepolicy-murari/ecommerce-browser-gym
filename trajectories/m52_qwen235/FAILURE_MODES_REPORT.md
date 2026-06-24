# Failure-mode report

- **Task**: `M52/unit_price_trap`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_best_value_pack`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 3})
- **missed required milestones**: ['ordered_best_value_pack']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `adfab6f0` (seed 0, stalled at step 0, 11 steps)
