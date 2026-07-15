# Failure-mode report

- **Task**: `M117/ambiguous_default_card_two_new`
- **Model**: `claude-opus-4-8`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: none
- **app path**: shop -> mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `3d7895e7` (seed 2, stalled at step 1, 5 steps)
