# Failure-mode report

- **Task**: `M66/expedited_upgrade_default_card`
- **Model**: `claude-opus-4-8`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_monitor_clean`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['ordered_monitor_clean']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `f8a4d3d6` (seed 2, stalled at step 0, 39 steps)
