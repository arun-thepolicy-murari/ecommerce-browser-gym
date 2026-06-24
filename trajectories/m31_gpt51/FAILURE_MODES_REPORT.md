# Failure-mode report

- **Task**: `M31/reconciliation_desk`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:amounts_correct+approved_exact_set+grand_total_correct`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 3})
- **missed required milestones**: ['amounts_correct', 'approved_exact_set', 'grand_total_correct']
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `a4f20665` (seed 0, stalled at step 0, 53 steps)
