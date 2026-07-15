# -*- coding: utf-8 -*-
"""Global budget watchdog — a HARD ceiling across ALL concurrent screening batches.

The per-shard/per-batch --cap is billed against a cost-root tree. Even with a shared
cost-root, two batches launched separately can end up on different roots, giving each
its own independent $cap (the multiplied-ceiling bug at the batch level). This watchdog
is the belt-and-suspenders fix: it polls the REAL cumulative spend over one shared
parent (default trajectories/cascade_v2, which covers every batch + all prior runs)
and, if it crosses --cap, kills every cascade process so nothing can overrun the global
budget regardless of any batch's internal cost-root.

    python -m eval.budget_watchdog --cap 500 --root trajectories/cascade_v2 [--interval 20]

Prints a line each poll; on breach it pkills `eval.cascade_v2` / `eval.cascade_parallel`
and exits non-zero.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

from eval.cost_tracker import cost_of_tree


def _kill_cascades(pid=None):
    if pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        return
    for pat in ("eval.cascade_parallel", "eval.cascade_v2", "eval.cross_model_screen", "eval.run"):
        subprocess.run(["pkill", "-f", pat], check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=500.0)
    ap.add_argument("--root", default="trajectories/cascade_v2",
                    help="Shared parent whose ENTIRE tree is summed (covers all batches).")
    # FIX (b): 5s default poll (was 20s). With N concurrent frontier shards spending ~$1-2/s,
    # a 20s interval let ~$30 land between polls (the 2026-07-09 $171.96->$203.22 overshoot).
    # 5s bounds the between-poll overshoot to ~1/4 of that; the watchdog kills IN-FLIGHT
    # episodes on breach (pkill), so overshoot is bounded by the poll interval, not by
    # episodes finishing.
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between polls")
    # FIX (c): trip at a headroom margin BELOW the hard cap so that, even with the ~poll-
    # interval of concurrent overshoot, the effective ceiling stays <= the real cap. Trips
    # when spent >= cap * trip-frac. Default 0.90.
    ap.add_argument("--trip-frac", type=float, default=0.90,
                    help="fire at cap*trip_frac (headroom margin for concurrency overshoot)")
    ap.add_argument("--pid", type=int, default=None,
                    help="on breach, stop only this dedicated worker PID")
    # NOTE: intentionally NO Math.random/time-jitter — deterministic polling.
    args = ap.parse_args()

    trip = args.cap * args.trip_frac
    print(f"[watchdog] global cap ${args.cap:.0f} over {args.root} — trip at ${trip:.0f} "
          f"(cap x {args.trip_frac:.2f}), polling every {args.interval:.0f}s", flush=True)
    while True:
        spent, _ = cost_of_tree(args.root, verbose=False)
        pct = 100.0 * spent / args.cap if args.cap else 0.0
        print(f"[watchdog] cumulative ${spent:.2f} / ${args.cap:.0f} ({pct:.1f}%)", flush=True)
        if args.cap and spent >= trip:
            print(f"[watchdog] *** CAP TRIP (${spent:.2f} >= ${trip:.0f} = cap x {args.trip_frac:.2f}) — "
                  f"killing ALL cascade processes (hard cap ${args.cap:.0f}) ***", flush=True)
            _kill_cascades(args.pid)
            sys.exit(2)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
