# Failure-mode report

- **Task**: `M31/reconciliation_desk`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:amounts_correct+approved_exact_set+grand_total_correct`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['amounts_correct', 'approved_exact_set', 'grand_total_correct']
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `7783fe39` (seed 1, stalled at step 0, 22 steps)

### `missed:amounts_correct+approved_exact_set+grand_total_correct`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['amounts_correct', 'approved_exact_set', 'grand_total_correct']
- **app path**: (none)
- **fact gap (required facts never observed)**: ['mail.electronics_fee']
- **representative episode**: `cdde126e` (seed 2, stalled at step -1, 0 steps)
