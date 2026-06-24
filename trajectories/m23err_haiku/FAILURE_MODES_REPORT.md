# Failure-mode report

- **Task**: `M23/offsite_keeps_moving`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:lunch_veg_under_budget+meeting_after_3pm_free+notified_attendees+notified_dana`  —  2/3 (67%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1, 'never_reached_checkout': 1})
- **missed required milestones**: ['lunch_veg_under_budget', 'meeting_after_3pm_free', 'notified_attendees', 'notified_dana']
- **app path**: mail -> shop -> food -> calendar -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `ce43f94b` (seed 1, stalled at step 0, 45 steps)

### `missed:meeting_after_3pm_free+notified_attendees+notified_dana`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['meeting_after_3pm_free', 'notified_attendees', 'notified_dana']
- **app path**: mail -> shop -> food -> calendar -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `d2558f25` (seed 0, stalled at step 18, 62 steps)
