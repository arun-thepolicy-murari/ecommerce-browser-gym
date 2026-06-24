# Failure-mode report

- **Task**: `M23/offsite_keeps_moving`
- **Model**: `claude-sonnet-4-6`  ·  **UI variant**: `normal`
- **Runs**: 5  ·  **Successes**: 0  ·  **Failures**: 5  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:lunch_veg_under_budget+meeting_after_3pm_free+notified_dana`  —  3/5 (60%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2, 'repeated_failed_actions': 1})
- **missed required milestones**: ['lunch_veg_under_budget', 'meeting_after_3pm_free', 'notified_dana']
- **app path**: mail -> calendar -> food -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `d9345797` (seed 1, stalled at step 45, 50 steps)

### `missed:lunch_veg_under_budget+meeting_after_3pm_free+notified_attendees+notified_dana`  —  2/5 (40%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1, 'never_reached_checkout': 1})
- **missed required milestones**: ['lunch_veg_under_budget', 'meeting_after_3pm_free', 'notified_attendees', 'notified_dana']
- **app path**: mail -> calendar -> food -> mail -> food -> calendar -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `031fb87f` (seed 0, stalled at step 0, 49 steps)
