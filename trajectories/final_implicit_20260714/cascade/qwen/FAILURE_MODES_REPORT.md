# Failure-mode report

- **Task**: `M383/internal_workshop_company_addresses_only`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:corporate_attendees_notified_and_user_confirmed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['corporate_attendees_notified_and_user_confirmed']
- **app path**: calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `dfabfa13` (seed 2, stalled at step 0, 9 steps)
