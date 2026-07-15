# Failure-mode report

- **Task**: `M344/latest_rsvp_selects_package`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:ordered_four_classics_and_emailed`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['ordered_four_classics_and_emailed']
- **app path**: mail -> food -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `ae5007df` (seed 2, stalled at step 0, 24 steps)
