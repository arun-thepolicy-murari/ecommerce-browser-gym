# Failure-mode report

- **Task**: `M142/no_monitor_in_stock_high_rating`
- **Model**: `gpt-5.6-sol`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `confirmation_page_missed`  (breakdown: {'confirmation_page_missed': 1})
- **missed required milestones**: none
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `c0a3de6a` (seed 2, stalled at step 1, 30 steps)
