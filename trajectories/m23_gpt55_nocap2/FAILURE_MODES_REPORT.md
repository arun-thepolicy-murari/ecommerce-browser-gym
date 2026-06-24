# Failure-mode report

- **Task**: `M23/offsite_keeps_moving`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 2  ·  **Successes**: 1  ·  **Failures**: 1  (failure rate **50%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:meeting_after_3pm_free+notified_attendees+notified_dana`  —  1/2 (50%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['meeting_after_3pm_free', 'notified_attendees', 'notified_dana']
- **app path**: mail -> calendar -> food -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `40dd810d` (seed 1, stalled at step 17, 50 steps)
