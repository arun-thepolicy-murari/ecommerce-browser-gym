# Failure-mode report

- **Task**: `M61/auto_refill_dead_card`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:set_up_refill`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 3})
- **missed required milestones**: ['set_up_refill']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `cd740dc4` (seed 0, stalled at step 0, 64 steps)
