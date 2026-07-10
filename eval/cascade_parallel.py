# -*- coding: utf-8 -*-
"""Phase 1 speedup — run cascade_v2 over a task list SHARDED across N isolated
servers concurrently (each shard = its own server + global world, so they never
clobber each other; same pattern as the Phase 0.4 oracle run).

Episodes are I/O-bound (waiting on the LLM API), so N concurrent shards cut wall
time ~N-fold. Each shard runs the full per-task escalation protocol independently;
we merge their coverage_matrix_v2.csv files at the end.

Budget: every shard is given --cap AND --cost-root=<shared parent>, so each shard's
per-seed cap check bills the ENTIRE parent tree (all shards) via cost_of_tree, i.e.
the cap is enforced GLOBALLY, not per-shard. (Previously each shard billed only its
own ~1/N slice, so the effective ceiling was N x --cap — a real safeguard hole.) The
first shard to observe global spend >= cap halts; the others halt on their next seed
boundary, so overshoot is bounded to ~N in-flight episodes.

Usage:
    python -m eval.cascade_parallel --tasks a,b,c,... --out DIR --shards 5 \
        --base-port 8050 --cap 500
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

from eval.cost_tracker import cost_of_tree


def shard_tasks(tasks, n):
    groups = [[] for _ in range(n)]
    for i, t in enumerate(tasks):           # round-robin for even difficulty spread
        groups[i % n].append(t)
    return [g for g in groups if g]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shards", type=int, default=5)
    ap.add_argument("--base-port", type=int, default=8050)
    ap.add_argument("--cap", type=float, default=500.0)
    ap.add_argument("--cost-root", default=None,
                    help="Tree the --cap is billed against (default: --out). Point MULTIPLE "
                         "concurrently-launched batches at ONE shared parent so the cap is "
                         "global ACROSS batches — otherwise each batch gets its own independent "
                         "$cap (the multiplied-ceiling bug, at the batch level).")
    ap.add_argument("--start-tier", default="qwen",
                    help="Resume every shard's cascade at this tier (tasks must have ALREADY "
                         "broken the lower tiers in a prior run). Forwarded to cascade_v2.")
    args = ap.parse_args()

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cost_root = args.cost_root or str(out)   # shared parent for cross-batch global cap
    groups = shard_tasks(tasks, args.shards)
    print(f"[parallel] {len(tasks)} tasks across {len(groups)} shard(s)", flush=True)

    procs = []
    for i, g in enumerate(groups):
        shard_out = out / f"shard_{i}"
        port = args.base_port + i * 2          # +2 spacing (cascade_v2 uses one port)
        logf = open(out / f"shard_{i}.log", "w")
        p = subprocess.Popen(
            [sys.executable, "-m", "eval.cascade_v2",
             "--tasks", ",".join(g), "--out", str(shard_out),
             "--base-port", str(port), "--cap", str(args.cap),
             "--cost-root", cost_root,          # cap billed over this tree (shared across batches if set)
             "--start-tier", args.start_tier],
            stdout=logf, stderr=subprocess.STDOUT)
        procs.append((i, p, logf))
        print(f"[parallel] shard {i}: pid {p.pid} port {port} — {len(g)} task(s)", flush=True)
        time.sleep(2)                          # stagger server starts

    fail = 0
    for i, p, logf in procs:
        rc = p.wait()
        logf.close()
        if rc != 0:
            fail += 1
            print(f"[parallel] shard {i} exited rc={rc}", flush=True)

    # merge all shard coverage_matrix_v2.csv into one
    merged = out / "coverage_matrix_v2.csv"
    header = None
    rows = []
    for i, _, _ in procs:
        f = out / f"shard_{i}" / "coverage_matrix_v2.csv"
        if not f.exists():
            print(f"[parallel] WARNING shard {i}: no coverage_matrix_v2.csv", flush=True)
            continue
        with open(f, newline="") as fh:
            r = csv.reader(fh)
            h = next(r)
            header = header or h
            rows.extend(r)
    if header:
        with open(merged, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        print(f"[parallel] merged {len(rows)} task rows -> {merged}", flush=True)

    print("[parallel] aggregate cost across all shards:", flush=True)
    total, _ = cost_of_tree(str(out), cap=args.cap)     # layout-independent: recurses all shards
    print(f"[parallel] TOTAL spend this run: ${total:.2f}", flush=True)
    print(f"[parallel] DONE (shard failures: {fail})", flush=True)


if __name__ == "__main__":
    main()
