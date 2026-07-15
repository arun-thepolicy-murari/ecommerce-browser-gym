# Failure-mode report

- **Task**: `M197/event_supplies_sneaked_addon`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:calendar_reminder`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['calendar_reminder']
- **app path**: shop -> calendar -> mail -> shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `5d4d022f` (seed 2, stalled at step 39, 40 steps)
