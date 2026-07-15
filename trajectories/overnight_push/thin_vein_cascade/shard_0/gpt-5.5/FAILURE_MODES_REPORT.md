# Failure-mode report

- **Task**: `M348/notify_everyone_except_included_dana`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:emailed_user_conflict`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['emailed_user_conflict']
- **app path**: calendar -> food -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `3eb71f84` (seed 2, stalled at step 0, 12 steps)
