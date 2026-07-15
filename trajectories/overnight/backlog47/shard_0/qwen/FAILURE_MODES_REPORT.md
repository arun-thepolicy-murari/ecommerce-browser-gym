# Failure-mode report

- **Task**: `M218/cancel_gated_on_shipment_status`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:cancelled_unshipped_and_emailed`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['cancelled_unshipped_and_emailed']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `8c3caa84` (seed 2, stalled at step 1, 34 steps)
