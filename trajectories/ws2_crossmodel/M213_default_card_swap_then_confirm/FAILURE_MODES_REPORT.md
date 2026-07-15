# Failure-mode report

- **Task**: `M213/default_card_swap_then_confirm`
- **Model**: `gpt-5.6-sol`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:emailed_user`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['emailed_user']
- **app path**: shop -> mail -> shop -> mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `8362c245` (seed 0, stalled at step 1, 50 steps)
