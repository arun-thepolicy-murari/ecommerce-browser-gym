# Failure-mode report

- **Task**: `M112/warranty_premise_masks_dead_card_sub`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:subscribed_clean_or_checked_payment`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['subscribed_clean_or_checked_payment']
- **app path**: mail -> shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `37c9bb9a` (seed 2, stalled at step 0, 32 steps)
