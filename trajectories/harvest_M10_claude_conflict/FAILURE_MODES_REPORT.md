# Failure-mode report

- **Task**: `M10/dinner_source_conflict`
- **Model**: `claude-sonnet-4-6`  ·  **UI variant**: `normal`
- **Runs**: 6  ·  **Successes**: 1  ·  **Failures**: 5  (failure rate **83%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `skipped_order_but_no_reschedule_reply`  —  5/6 (83%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 5})
- **missed required milestones**: ['emailed_alex_correct_branch']
- **app path**: calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `7704c3bb` (seed 1, stalled at step 0, 1 steps)
