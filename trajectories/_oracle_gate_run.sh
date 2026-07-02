#!/usr/bin/env bash
# Phase 0.4 — oracle gate. Run the hand-coded oracle over ALL 234 tasks x seeds 0,1,2,
# sharded across K isolated servers (the gym holds ONE global world per server, so each
# shard needs its own server; episodes within a shard stay sequential).
set -u
cd /Users/maroonferrari/Deccan/ecommerce-browser-gym
VENV=.venv/bin
K=6
BASE_PORT=8010
OUT=trajectories/oracle_phase0
LOGDIR=/tmp/oracle_gate
rm -rf "$LOGDIR" && mkdir -p "$LOGDIR"
mkdir -p "$OUT"

TASKS=()
while IFS= read -r line; do
  [ -n "$line" ] && TASKS+=("$line")
done < /tmp/all_tasks.txt
N=${#TASKS[@]}
echo "sharding $N tasks across $K servers"

# start K servers
SERVER_PIDS=()
for i in $(seq 0 $((K-1))); do
  PORT=$((BASE_PORT+i))
  $VENV/uvicorn server.main:app --port $PORT > "$LOGDIR/server_$PORT.log" 2>&1 &
  SERVER_PIDS+=($!)
done
echo "started servers pids: ${SERVER_PIDS[*]}"

# wait for all servers healthy
for i in $(seq 0 $((K-1))); do
  PORT=$((BASE_PORT+i))
  for _ in $(seq 1 60); do
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/_harness/tasks" 2>/dev/null | grep -q 200; then
      echo "server $PORT up"; break
    fi
    sleep 1
  done
done

# build shard task-lists (round-robin for even difficulty spread)
declare -a SHARD
for idx in "${!TASKS[@]}"; do
  s=$((idx % K))
  if [ -z "${SHARD[$s]:-}" ]; then SHARD[$s]="${TASKS[$idx]}"; else SHARD[$s]="${SHARD[$s]},${TASKS[$idx]}"; fi
done

# launch one eval.run per shard against its own server
RUN_PIDS=()
for i in $(seq 0 $((K-1))); do
  PORT=$((BASE_PORT+i))
  $VENV/python -m eval.run --agent oracle \
      --tasks "${SHARD[$i]}" --seeds 0,1,2 \
      --server "http://localhost:$PORT" --headless --no-video \
      --out-traj "$OUT" > "$LOGDIR/shard_$i.log" 2>&1 &
  RUN_PIDS+=($!)
done
echo "launched ${#RUN_PIDS[@]} shard runners: ${RUN_PIDS[*]}"

# wait for all shard runners
FAIL=0
for pid in "${RUN_PIDS[@]}"; do
  if ! wait "$pid"; then FAIL=1; echo "shard pid $pid exited non-zero"; fi
done

# tear down servers
for pid in "${SERVER_PIDS[@]}"; do kill "$pid" 2>/dev/null; done

echo "ALL SHARDS DONE (fail=$FAIL)"
echo "trajectories written: $(ls "$OUT" | wc -l)"
