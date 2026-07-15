# Failure-mode report

- **Task**: `M314/printer_ink_wrong_cartridge_offpath_model`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:resolved_compat_emailed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['resolved_compat_emailed']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `6ba93915` (seed 2, stalled at step 1, 36 steps)
