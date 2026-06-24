# Failure-mode report

- **Task**: `M32/coupled_offsite`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:offsite_at_16`  —  2/3 (67%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: ['offsite_at_16']
- **app path**: mail -> shop -> food -> mail -> calendar -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `9f1471a1` (seed 0, stalled at step 72, 83 steps)

### `missed:attendees_notified+offsite_at_16`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['attendees_notified', 'offsite_at_16']
- **app path**: mail -> shop -> food -> mail -> calendar -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `9149f28e` (seed 2, stalled at step 73, 79 steps)
