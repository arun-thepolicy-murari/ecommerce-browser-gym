# Failure-mode report

- **Task**: `M32/coupled_offsite`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:attendees_notified+offsite_at_16`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['attendees_notified', 'offsite_at_16']
- **app path**: mail -> shop -> food -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `71d1f5f9` (seed 0, stalled at step 84, 91 steps)

### `missed:attendees_notified`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['attendees_notified']
- **app path**: mail -> shop -> food -> calendar -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `b852c2b4` (seed 1, stalled at step 67, 74 steps)
