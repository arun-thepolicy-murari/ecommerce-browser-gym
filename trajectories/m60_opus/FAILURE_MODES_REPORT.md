# Failure-mode report

- **Task**: `M60/stale_gift_address`
- **Model**: `claude-opus-4-8`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_gift_to_sister`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['ordered_gift_to_sister']
- **app path**: (none)
- **fact gap (required facts never observed)**: none
- **representative episode**: `d373608e` (seed 0, stalled at step -1, 0 steps)
