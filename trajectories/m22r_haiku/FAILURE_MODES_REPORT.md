# Failure-mode report

- **Task**: `M22/async_calendar_cascade`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 2  ·  **Failures**: 1  (failure rate **33%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:coffee_ordered`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['coffee_ordered']
- **app path**: food -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: ['mail.new_meeting_time']
- **representative episode**: `2693a1e7` (seed 0, stalled at step 37, 38 steps)
