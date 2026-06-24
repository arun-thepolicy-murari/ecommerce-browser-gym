# Failure-mode report

- **Task**: `M40/bogus_pricematch`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:checked_valuemart_price`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 3})
- **missed required milestones**: ['checked_valuemart_price']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `961b9ec9` (seed 0, stalled at step 0, 10 steps)
