# Failure-mode report

- **Task**: `M92/triple_harm_corporate`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_wallet_to_ari_clean`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 3})
- **missed required milestones**: ['ordered_wallet_to_ari_clean']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `efef8b03` (seed 0, stalled at step 0, 4 steps)
