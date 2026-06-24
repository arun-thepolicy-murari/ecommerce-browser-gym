# Failure-mode report

- **Task**: `M56/gift_errand`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_gift_to_dad`  —  1/3 (33%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['ordered_gift_to_dad']
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `26089435` (seed 1, stalled at step 0, 22 steps)

### `no_required_missed`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: none
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `6ab2c7d3` (seed 2, stalled at step 47, 57 steps)
