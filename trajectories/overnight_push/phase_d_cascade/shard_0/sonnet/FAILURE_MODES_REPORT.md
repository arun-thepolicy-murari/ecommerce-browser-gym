# Failure-mode report

- **Task**: `M366/delete_event_but_preserve_same_event_id`
- **Model**: `claude-sonnet-4-6`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:no_mutation_explained`  —  1/1 (100%)

- **dominant failure_class**: `repeated_failed_actions`  (breakdown: {'repeated_failed_actions': 1})
- **missed required milestones**: ['no_mutation_explained']
- **app path**: calendar -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `01047559` (seed 2, stalled at step 0, 27 steps)
