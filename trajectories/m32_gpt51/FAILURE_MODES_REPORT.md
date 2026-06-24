# Failure-mode report

- **Task**: `M32/coupled_offsite`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:attendees_notified+finance_told_exact_total+offsite_at_16`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['attendees_notified', 'finance_told_exact_total', 'offsite_at_16']
- **app path**: mail -> shop -> food -> calendar -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `c06b9b89` (seed 0, stalled at step 13, 69 steps)

### `missed:attendees_notified+offsite_at_16`  —  1/3 (33%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['attendees_notified', 'offsite_at_16']
- **app path**: mail -> food -> calendar -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `4eda8c62` (seed 1, stalled at step 63, 74 steps)

### `missed:attendees_notified+finance_told_exact_total+offsite_at_16`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['attendees_notified', 'finance_told_exact_total', 'offsite_at_16']
- **app path**: mail -> food -> calendar
- **fact gap (required facts never observed)**: ['mail.new_eta']
- **representative episode**: `6a069bc5` (seed 2, stalled at step 10, 43 steps)
