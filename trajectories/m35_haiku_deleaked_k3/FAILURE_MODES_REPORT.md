# Failure-mode report

- **Task**: `M35/lying_bounce`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  2/3 (67%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: none
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `9a736d11` (seed 1, stalled at step 14, 23 steps)
