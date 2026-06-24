# Failure-mode report

- **Task**: `M16/coordinated_dinner_delay`
- **Model**: `claude-haiku-4-5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 1  ·  **Failures**: 2  (failure rate **67%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reflects_new_eta_only`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['calendar_reflects_new_eta_only']
- **app path**: food -> calendar -> mail -> calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `db64fa61` (seed 0, stalled at step 47, 48 steps)

### `missed:calendar_reflects_new_eta_only+emailed_guest_new_eta`  —  1/3 (33%)  ⭐ STATISTICALLY SIGNIFICANT

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['calendar_reflects_new_eta_only', 'emailed_guest_new_eta']
- **app path**: food -> calendar -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `1f839d09` (seed 2, stalled at step 10, 48 steps)
