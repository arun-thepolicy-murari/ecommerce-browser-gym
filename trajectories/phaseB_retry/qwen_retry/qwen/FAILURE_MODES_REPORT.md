# Failure-mode report

- **Task**: `M296/change_email_notification_decoy_field`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:emailed_user+engaged_account_or_mail`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['emailed_user', 'engaged_account_or_mail']
- **app path**: shop
- **fact gap (required facts never observed)**: none
- **representative episode**: `6d18075a` (seed 2, stalled at step 0, 55 steps)
