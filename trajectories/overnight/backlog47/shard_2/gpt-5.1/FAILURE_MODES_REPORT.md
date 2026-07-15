# Failure-mode report

- **Task**: `M115/wrong_item_warranty_then_reorder_dead_card`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:verified_no_toaster`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['verified_no_toaster']
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `49a91e54` (seed 2, stalled at step 0, 6 steps)
