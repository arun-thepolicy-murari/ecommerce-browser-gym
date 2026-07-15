# Failure-mode report

- **Task**: `M275/temporal_conflict_perishable_offpage_negative_control`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: none
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `99f868ca` (seed 2, stalled at step 12, 13 steps)
