#!/usr/bin/env bash
# Phase-1 screening launcher — captures the two env gotchas that cost us debug time:
#   (1) .env uses bare KEY=val (no export), so `set -a` is required or the shard
#       subprocesses see no API keys ("qwen: key missing — STOPPING cascade").
#   (2) playwright lives in ./.venv, NOT system python3; cascade_parallel spawns
#       shards via sys.executable, so it MUST be launched with ./.venv/bin/python
#       ("No module named 'playwright'").
# The fixed global cap is automatic: cascade_parallel passes --cost-root=<out> to
# every shard, so --cap is enforced across ALL shards, not per-shard.
#
# Usage:
#   eval/run_screen.sh <name> <comma-separated-task-ids> [shards] [base_port] [cap] [cost_root]
# Example:
#   eval/run_screen.sh batch5_source_anchoring "M42/...,M53/..." 6 8080 500
#
# cost_root: point CONCURRENT batches at ONE shared parent (e.g. trajectories/cascade_v2)
# so --cap is enforced GLOBALLY across them. Omit it and each batch gets its own
# independent $cap — the multiplied-ceiling bug at the batch level. For a hard global
# ceiling regardless of internal cost-roots, also run eval/budget_watchdog.py.
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="${1:?need a batch name, e.g. batch5_source_anchoring}"
TASKS="${2:?need comma-separated task ids}"
SHARDS="${3:-6}"
BASE_PORT="${4:-8060}"
CAP="${5:-500}"
COST_ROOT="${6:-}"

OUT="trajectories/cascade_v2/${NAME}"
PY="./.venv/bin/python"
[ -x "$PY" ] || { echo "FATAL: $PY not found (need the venv with playwright)"; exit 1; }

# (1) export the .env keys to the environment the shards inherit
set -a; source .env; set +a
for k in QWEN_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY; do
  [ -n "${!k:-}" ] || { echo "FATAL: $k not set after sourcing .env"; exit 1; }
done
echo "[run_screen] keys OK; launching '$NAME' — $(echo "$TASKS" | tr ',' '\n' | wc -l | tr -d ' ') task(s), ${SHARDS} shard(s), cap \$${CAP} (GLOBAL across shards)"

rm -rf "$OUT" "${OUT}.launch.log"
CR_ARG=(); [ -n "$COST_ROOT" ] && CR_ARG=(--cost-root "$COST_ROOT") && \
  echo "[run_screen] cost-root=$COST_ROOT (cap shared across batches under it)"
nohup "$PY" -m eval.cascade_parallel \
  --tasks "$TASKS" --out "$OUT" \
  --shards "$SHARDS" --base-port "$BASE_PORT" --cap "$CAP" "${CR_ARG[@]}" \
  > "${OUT}.launch.log" 2>&1 &
echo "[run_screen] pid $! — logs: ${OUT}.launch.log and ${OUT}/shard_*.log"
echo "[run_screen] watch:  find ${OUT} -name '*.jsonl' | wc -l   |   tail -f ${OUT}/shard_0.log"
