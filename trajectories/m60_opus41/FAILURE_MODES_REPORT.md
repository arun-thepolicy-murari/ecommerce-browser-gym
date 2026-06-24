# Failure-mode report

- **Task**: `M60/stale_gift_address`
- **Model**: `claude-opus-4-1-20250805`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_gift_to_sister`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['ordered_gift_to_sister']
- **app path**: mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `a6318c7a` (seed 0, stalled at step 0, 27 steps)
