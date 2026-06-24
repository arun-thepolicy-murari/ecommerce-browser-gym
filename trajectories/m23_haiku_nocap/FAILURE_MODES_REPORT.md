# Failure-mode report

- **Task**: `M23/offsite_keeps_moving`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 2  ·  **Successes**: 0  ·  **Failures**: 2  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:meeting_after_3pm_free+notified_attendees+notified_dana`  —  2/2 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: ['meeting_after_3pm_free', 'notified_attendees', 'notified_dana']
- **app path**: mail -> calendar -> shop -> food -> mail
- **fact gap (required facts never observed)**: ['calendar.final_slot']
- **representative episode**: `ad5c366f` (seed 0, stalled at step 40, 66 steps)
