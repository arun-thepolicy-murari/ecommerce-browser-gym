# Failure-mode report

- **Task**: `M309/vip_discount_false_spend_gate_offpath`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:resolved_gate_emailed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['resolved_gate_emailed']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `772d65bc` (seed 2, stalled at step 1, 22 steps)
