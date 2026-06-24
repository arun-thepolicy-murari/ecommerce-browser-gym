# Failure-mode report

- **Task**: `M16/coordinated_dinner_delay`
- **Model**: `gpt-4.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reflects_new_eta_only+emailed_guest_new_eta+food_order_placed+noticed_delay`  —  3/3 (100%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 2, 'never_reached_checkout': 1})
- **missed required milestones**: ['calendar_reflects_new_eta_only', 'emailed_guest_new_eta', 'food_order_placed', 'noticed_delay']
- **app path**: food
- **fact gap (required facts never observed)**: ['calendar.user_event_time', 'mail.new_eta']
- **representative episode**: `51abf9dc` (seed 0, stalled at step 0, 50 steps)
