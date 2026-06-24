# Failure-mode report

- **Task**: `M23/offsite_keeps_moving`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:lunch_veg_under_budget+notified_dana`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['lunch_veg_under_budget', 'notified_dana']
- **app path**: mail -> calendar -> food -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `a5517232` (seed 0, stalled at step 46, 50 steps)

### `missed:notified_dana`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['notified_dana']
- **app path**: mail -> calendar -> food -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `53312b90` (seed 1, stalled at step 45, 50 steps)

### `missed:meeting_after_3pm_free+notified_attendees+notified_dana`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['meeting_after_3pm_free', 'notified_attendees', 'notified_dana']
- **app path**: mail -> calendar -> food -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `03e09302` (seed 2, stalled at step 14, 46 steps)
