# Failure-mode report

- **Task**: `M16/coordinated_dinner_delay`
- **Model**: `gpt-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reflects_new_eta_only+emailed_guest_new_eta+noticed_delay`  —  2/3 (67%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: ['calendar_reflects_new_eta_only', 'emailed_guest_new_eta', 'noticed_delay']
- **app path**: food -> calendar
- **fact gap (required facts never observed)**: ['calendar.user_event_time', 'mail.new_eta']
- **representative episode**: `1579b238` (seed 1, stalled at step 0, 50 steps)

### `missed:calendar_reflects_new_eta_only+emailed_guest_new_eta`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['calendar_reflects_new_eta_only', 'emailed_guest_new_eta']
- **app path**: food -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `3aa17e29` (seed 0, stalled at step 49, 50 steps)
