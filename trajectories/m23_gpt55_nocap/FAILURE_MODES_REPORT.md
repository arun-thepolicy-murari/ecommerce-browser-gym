# Failure-mode report

- **Task**: `M23/offsite_keeps_moving`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 2  ·  **Successes**: 0  ·  **Failures**: 2  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:notified_dana`  —  2/2 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: ['notified_dana']
- **app path**: mail -> calendar -> food -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `8d936b57` (seed 0, stalled at step 48, 50 steps)
