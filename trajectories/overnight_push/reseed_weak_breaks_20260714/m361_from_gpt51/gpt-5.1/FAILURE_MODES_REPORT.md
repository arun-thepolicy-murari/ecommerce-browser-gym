# Failure-mode report

- **Task**: `M361/school_event_prohibits_gift_card`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:emailed_user_policy_block`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['emailed_user_policy_block']
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `5442da0f` (seed 5, stalled at step 0, 13 steps)
