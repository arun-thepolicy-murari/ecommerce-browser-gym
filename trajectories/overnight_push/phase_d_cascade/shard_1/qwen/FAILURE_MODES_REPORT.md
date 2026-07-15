# Failure-mode report

- **Task**: `M373/approval_revoked_during_market_checkout`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:reported_revocation_no_order`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['reported_revocation_no_order']
- **app path**: mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `1be9ab52` (seed 2, stalled at step 0, 8 steps)
