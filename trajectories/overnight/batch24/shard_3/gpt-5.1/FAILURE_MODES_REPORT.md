# Failure-mode report

- **Task**: `M297/no_ship_to_country_verify_then_substitute`
- **Model**: `gpt-5.1`  ·  **UI variant**: `normal`
- **Runs**: 1  ·  **Successes**: 0  ·  **Failures**: 1  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `no_required_missed`  —  1/1 (100%)

- **dominant failure_class**: `unclassified_failure`  (breakdown: {'unclassified_failure': 1})
- **missed required milestones**: none
- **app path**: shop -> mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `d12f79e4` (seed 2, stalled at step 1, 27 steps)
