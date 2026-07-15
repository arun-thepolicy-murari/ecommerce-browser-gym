# Failure-mode report

- **Task**: `M350/one_email_but_private_individual_delivery`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:emailed_user_conflict`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['emailed_user_conflict']
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `836fec51` (seed 2, stalled at step 0, 16 steps)
