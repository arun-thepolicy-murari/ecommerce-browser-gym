# Failure-mode report

- **Task**: `M202/dogfood_coverage_join`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:net_coverage_correct`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 3})
- **missed required milestones**: ['net_coverage_correct']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `d30f2430` (seed 0, stalled at step 17, 18 steps)
