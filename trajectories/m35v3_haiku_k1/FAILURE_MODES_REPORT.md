# Failure-mode report

- **Task**: `M35/lying_bounce`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: none
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `26a3b90f` (seed 0, stalled at step 16, 29 steps)
