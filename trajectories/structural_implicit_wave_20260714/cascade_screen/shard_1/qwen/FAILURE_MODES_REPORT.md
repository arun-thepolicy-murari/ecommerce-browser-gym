# Failure-mode report

- **Task**: `M380/earliest_uncovered_training_supplies`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:first_aid_four_kits_and_report`  —  1/1 (100%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: ['first_aid_four_kits_and_report']
- **app path**: calendar -> mail -> calendar -> mail -> calendar -> mail -> calendar
- **fact gap (required facts never observed)**: none
- **representative episode**: `44c6ccc2` (seed 2, stalled at step 0, 37 steps)
