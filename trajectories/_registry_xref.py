# -*- coding: utf-8 -*-
"""Phase 0.3 — registry cross-reference / orphan check.

The repo wires each task through several independent dicts. A task id present in one
but missing from another is an ORPHAN — it will silently mis-wire (no brief, no
verifier, no oracle, wrong start). This script pulls the key set from every registry
and flags asymmetries.

KEY CONVENTIONS (verified against the code, not assumed):
  * Full-id registries key by "SHORT/slug", e.g. "A1/buy_wireless_mouse":
        TASKS, SUITE_FACTORIES, SOLVERS, START_PATHS, REQUIRED_FACTS
  * BRIEFS keys by the SHORT id only ("A1") and is looked up at runtime as
        BRIEFS[task_id.split("/")[0]]  (server/tasks.py). So BRIEFS is compared on the
        set of short prefixes of the full-id universe, NOT on full ids.

Registries are grouped by intent:

  TOTAL (must cover every task, identical key sets after prefix-normalisation):
    BRIEFS          server/tasks.py     — task instructions        (short-id keyed)
    TASKS           server/tasks.py     — world/state factory functions
    SUITE_FACTORIES server/verifiers.py — milestone verifier suites
    SOLVERS         agents/oracle_agent — hand-coded gold solvers

  PARTIAL-BY-DESIGN (runtime supplies a documented default for missing ids):
    START_PATHS     server/tasks.py     — START_PATHS.get(id, "/")   default "/"
    REQUIRED_FACTS  server/tasks.py     — REQUIRED_FACTS.get(id, []) default []

Gate (hard fail on any):
  * the four TOTAL registries do not all share one identical key set
  * SOLVERS \\ SUITE_FACTORIES  is non-empty (oracle for a task with no verifier)
  * SUITE_FACTORIES \\ SOLVERS  is non-empty (verifier for a task with no oracle)

Partial registries are reported (their gaps + the default that covers them) but do not
fail the gate, since consumption sites default them explicitly.

SOLVERS is read via AST so this script needs no playwright (oracle_agent imports the
browser runner at module load).
"""
import ast
import json
import sys

from server.tasks import BRIEFS, START_PATHS, REQUIRED_FACTS, TASKS
from server.verifiers import SUITE_FACTORIES


def solver_keys_via_ast(path="agents/oracle_agent.py"):
    """Extract the string keys of the top-level SOLVERS = {...} dict without importing
    the module (its import chain pulls in playwright)."""
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "SOLVERS":
                    if not isinstance(node.value, ast.Dict):
                        raise SystemExit("SOLVERS is not a dict literal — adjust extractor")
                    keys = []
                    for k in node.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.append(k.value)
                        else:
                            raise SystemExit(f"non-string/dynamic SOLVERS key: {ast.dump(k)}")
                    return set(keys)
    raise SystemExit("SOLVERS assignment not found")


def main():
    # full-id registries
    full_reg = {
        "TASKS": set(TASKS),
        "SUITE_FACTORIES": set(SUITE_FACTORIES),
        "SOLVERS": solver_keys_via_ast(),
        "START_PATHS": set(START_PATHS),
        "REQUIRED_FACTS": set(REQUIRED_FACTS),
    }
    briefs_short = set(BRIEFS)   # short-id keyed

    full_total_names = ["TASKS", "SUITE_FACTORIES", "SOLVERS"]
    partial_names = ["START_PATHS", "REQUIRED_FACTS"]
    defaults = {"START_PATHS": '"/"', "REQUIRED_FACTS": "[]"}

    print("=== registry sizes ===")
    print(f"   {'BRIEFS':<16} {len(briefs_short):>4}  (TOTAL, short-id keyed)")
    for name in full_reg:
        tag = "TOTAL" if name in full_total_names else "partial"
        print(f"   {name:<16} {len(full_reg[name]):>4}  ({tag}, full-id keyed)")

    # canonical universe = union of the full-id TOTAL registries
    universe = set().union(*(full_reg[n] for n in full_total_names))
    universe_short = {t.split("/")[0] for t in universe}
    print(f"\n   universe (full ids): {len(universe)}; distinct short prefixes: {len(universe_short)}")
    if len(universe_short) != len(universe):
        # two full ids sharing a short prefix would make BRIEFS ambiguous
        from collections import Counter
        dupes = {k: v for k, v in Counter(t.split('/')[0] for t in universe).items() if v > 1}
        failures_prefix = ("PREFIX_COLLISION", "ambiguous", dupes)
    else:
        failures_prefix = None

    failures = []
    if failures_prefix:
        failures.append(failures_prefix)
        print(f"   !! prefix collisions (BRIEFS lookup ambiguous): {failures_prefix[2]}")

    print("\n=== full-id TOTAL registries must equal the universe ===")
    for name in full_total_names:
        missing = sorted(universe - full_reg[name])
        extra = sorted(full_reg[name] - universe)
        if missing:
            failures.append((name, "missing", missing))
            print(f"   !! {name}: MISSING {len(missing)}: {missing[:20]}")
        if extra:
            failures.append((name, "extra", extra))
            print(f"   !! {name}: EXTRA {len(extra)}: {extra[:20]}")
        if not missing and not extra:
            print(f"   OK {name}: complete ({len(full_reg[name])})")

    print("\n=== BRIEFS (short-id) must equal the set of universe prefixes ===")
    briefs_missing = sorted(universe_short - briefs_short)
    briefs_extra = sorted(briefs_short - universe_short)
    if briefs_missing:
        failures.append(("BRIEFS", "missing", briefs_missing))
        print(f"   !! BRIEFS: MISSING {len(briefs_missing)}: {briefs_missing[:20]}")
    if briefs_extra:
        failures.append(("BRIEFS", "extra", briefs_extra))
        print(f"   !! BRIEFS: EXTRA {len(briefs_extra)}: {briefs_extra[:20]}")
    if not briefs_missing and not briefs_extra:
        print(f"   OK BRIEFS: one brief per task, bijective ({len(briefs_short)})")

    print("\n=== bidirectional SOLVERS <-> SUITE_FACTORIES ===")
    only_solver = sorted(full_reg["SOLVERS"] - full_reg["SUITE_FACTORIES"])
    only_suite = sorted(full_reg["SUITE_FACTORIES"] - full_reg["SOLVERS"])
    if only_solver:
        failures.append(("SOLVERS_without_SUITE", "orphan", only_solver))
        print(f"   !! oracle SOLVERS with NO verifier suite ({len(only_solver)}): {only_solver[:20]}")
    else:
        print("   OK every SOLVERS id has a SUITE_FACTORIES entry")
    if only_suite:
        failures.append(("SUITE_without_SOLVER", "orphan", only_suite))
        print(f"   !! SUITE_FACTORIES with NO oracle solver ({len(only_suite)}): {only_suite[:20]}")
    else:
        print("   OK every SUITE_FACTORIES id has a SOLVERS entry")

    print("\n=== partial-by-design registries (reported, not gated) ===")
    for name in partial_names:
        gaps = sorted(universe - full_reg[name])
        extra = sorted(full_reg[name] - universe)   # keys not in any total registry = real orphan
        print(f"   {name}: {len(gaps)} ids use default {defaults[name]}"
              + (f"; first few gaps: {gaps[:10]}" if gaps else ""))
        if extra:
            failures.append((name, "extra_orphan", extra))
            print(f"   !! {name}: {len(extra)} keys not in ANY total registry: {extra[:20]}")

    all_sizes = {"BRIEFS": len(briefs_short), **{k: len(v) for k, v in full_reg.items()}}
    summary = {
        "sizes": all_sizes,
        "universe": len(universe),
        "failures": [(n, kind, ids) for (n, kind, ids) in failures],
        "n_failures": len(failures),
    }
    with open("trajectories/_registry_xref.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== SUMMARY ===")
    if failures:
        print(f"ORPHANS FOUND: {len(failures)} categories — see above")
        sys.exit(1)
    print("ZERO ORPHANS — all TOTAL registries share one key set; "
          "SOLVERS <-> SUITE_FACTORIES fully bijective")
    print("[wrote trajectories/_registry_xref.json]")
    sys.exit(0)


if __name__ == "__main__":
    main()
