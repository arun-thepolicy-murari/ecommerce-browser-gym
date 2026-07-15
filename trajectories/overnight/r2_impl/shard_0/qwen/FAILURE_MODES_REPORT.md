# Failure-mode report

- **Task**: `M312/usbc_cable_wont_fit_lightning_phone`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:resolved_compat_emailed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['resolved_compat_emailed']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `df1afea9` (seed 2, stalled at step 1, 13 steps)
