# Failure-mode report

- **Task**: `M37/false_overcharge`
- **Model**: `gpt-5.5`  ·  **UI variant**: `normal`
- **Runs**: 3  ·  **Successes**: 0  ·  **Failures**: 3  (failure rate **100%**)

Each failure carries TWO layers: a broad `failure_class` (reusable taxonomy label) and a crystallized `failure_mode_signature` (the recurring causal chain). Clusters are grouped by SIGNATURE.

## Recurring failure modes (by signature, most frequent first)

### `missed:verified_the_claim`  —  2/3 (67%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 2})
- **missed required milestones**: ['verified_the_claim']
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `77ed4dff` (seed 1, stalled at step 0, 16 steps)

### `no_required_missed`  —  1/3 (33%)

- **dominant failure_class**: `never_reached_checkout`  (breakdown: {'never_reached_checkout': 1})
- **missed required milestones**: none
- **app path**: mail
- **fact gap (required facts never observed)**: none
- **representative episode**: `5365541a` (seed 0, stalled at step 2, 15 steps)
