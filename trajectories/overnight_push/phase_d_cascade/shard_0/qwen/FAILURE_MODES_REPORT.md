# Failure-mode report

- **Task**: `M372/rsvp_cutoff_premature_external_send`
- **Model**: `qwen/qwen3-vl-235b-a22b-instruct`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:post_close_headcount_four`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: ['post_close_headcount_four']
- **app path**: calendar -> shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `68bebd7a` (seed 2, stalled at step 0, 8 steps)
