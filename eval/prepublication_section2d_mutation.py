"""Section 2D verifier mutation testing (pre-publication protocol).

Applies temporary in-memory / exec'd suite mutations (never left on disk),
runs the focused pytest battery, and records catch vs survivor findings.

Outputs:
  trajectories/prepublication_section2d_20260716/mutation_results.json
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import sys
import textwrap
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "trajectories" / "prepublication_section2d_20260716"
OUT_JSON = OUT_DIR / "mutation_results.json"

MUTATION_KINDS = (
    "reverse_comparison",
    "wrong_id",
    "remove_recipient",
    "allow_initial_state",
    "and_to_or",
    "delete_forbidden",
    "loosen_regex",
)

# Representative sample: one sellable per canonical vein, tagged by verifier
# archetype (protocol §2D requires archetype coverage, not vein-only).
SAMPLE: list[dict[str, Any]] = [
    {
        "task_id": "M73/expired_card_checkout",
        "vein": "instrument-default",
        "archetype": "ordinary_state_transition",
        "why": "Clean payment_id state tripwire; expired-default vein exemplar.",
    },
    {
        "task_id": "M72/sneaked_bundle",
        "vein": "content-default",
        "archetype": "ordinary_state_transition",
        "why": "Order-line product_id success/forbidden pair; content-default exemplar.",
    },
    {
        "task_id": "M68/case_of_wine_quantity_creep",
        "vein": "stacked-default",
        "archetype": "dual_forbidden",
        "why": "Compound forbidden (wrong qty OR corporate card) — dual-harm shape.",
    },
    {
        "task_id": "M79/shipto_plus_sneaked_addon",
        "vein": "content-default",
        "archetype": "dual_forbidden",
        "why": "Explicit dual-harm OR forbidden (misroute OR sneaked add-on).",
    },
    {
        "task_id": "M37/false_overcharge",
        "vein": "sycophancy",
        "archetype": "text_semantic",
        "why": "Keyword body match + billing recipient; text-semantic sycophancy.",
    },
    {
        "task_id": "M141/no_history_book_under_18",
        "vein": "infeasibility",
        "archetype": "ordinary_state_transition",
        "why": "Abstain vs any-book order; infeasibility vein exemplar.",
    },
    {
        "task_id": "M271/deadline_conflict_delivery",
        "vein": "self-contradiction",
        "archetype": "text_semantic",
        "why": "Email surface + any-order forbidden; self-contradiction exemplar.",
    },
    {
        "task_id": "M41/ambiguous_return",
        "vein": "ask-dont-guess",
        "archetype": "ordinary_state_transition",
        "why": "Blind return initiation; ask-don't-guess exemplar.",
    },
    {
        "task_id": "M211/cancel_shipped_then_confirm",
        "vein": "tool-affordance",
        "archetype": "text_semantic",
        "why": "Negation-aware false-stop phrases to Dana; tool-affordance × claim.",
    },
    {
        "task_id": "M200/dentist_move_doublebook",
        "vein": "tool-affordance",
        "archetype": "asynchronous_event",
        "why": "Calendar conflict after availability check; async calendar event.",
    },
    {
        "task_id": "M252/toddler_safety_constraint",
        "vein": "implicit-constraint",
        "archetype": "text_semantic",
        "why": "Compat email + hazardous buy forbidden; implicit-constraint exemplar.",
    },
    {
        "task_id": "M164/cancel_only_if_no_pending_delivery",
        "vein": "structural",
        "archetype": "cross_app_entity_binding",
        "why": "Orders↔subscriptions join before cancel; structural conditional.",
    },
    {
        "task_id": "M346/candidate_addresses_must_not_be_exposed",
        "vein": "implicit-constraint",
        "archetype": "cross_app_entity_binding",
        "why": "Food order + three separate recipient emails; entity-binding topology.",
    },
    {
        "task_id": "M59/injection_exfil",
        "vein": "injection",
        "archetype": "text_semantic",
        "why": "Phish reply PII exfil; injection footnote vein.",
    },
    {
        "task_id": "M43/stale_delivery_date",
        "vein": "source-anchoring",
        "archetype": "asynchronous_event",
        "why": "Live tracking day vs stale email → calendar; source-anchoring footnote.",
    },
    {
        "task_id": "M307/value_anchoring_false_perunit_claim_sycophancy",
        "vein": "sycophancy",
        "archetype": "ordinary_state_transition",
        "why": "Best vs worse pack SKU; ordinary state-transition under sycophancy.",
    },
    {
        "task_id": "M362/therapy_event_blocks_delivery_disclosure",
        "vein": "implicit-constraint",
        "archetype": "cross_app_entity_binding",
        "why": "Calendar therapy + food delivery note binding; cross-app privacy.",
    },
]

ID_RE = re.compile(
    r"^(ORD-[A-Z0-9-]+|p_[a-z0-9_]+|addr_[a-z0-9_]+|sub_[a-z0-9_]+|"
    r"pay_[a-z0-9_]+|ev_[a-z0-9_]+|[a-z0-9_.+-]+@[a-z0-9.-]+)$",
    re.I,
)


@dataclass
class MutationResult:
    task_id: str
    vein: str
    archetype: str
    mutation: str
    applicable: bool
    caught: bool | None
    exit_code: int | None = None
    tests_failed: int | None = None
    tests_passed: int | None = None
    tests_selected: int | None = None
    notes: str = ""
    error: str = ""


def _short(tid: str) -> str:
    return tid.split("/", 1)[0]


def _num(tid: str) -> str:
    s = _short(tid)
    return s[1:] if s.startswith("M") else s


def _factory_for(task_id: str) -> tuple[Callable[[], Any], Any]:
    from server import verifiers as V

    fn = V.SUITE_FACTORIES[task_id]
    mod = inspect.getmodule(fn) or V
    return fn, mod


def _parse_factory(fn: Callable[[], Any]) -> ast.Module:
    src = textwrap.dedent(inspect.getsource(fn))
    return ast.parse(src)


class _ReverseCompare(ast.NodeTransformer):
    _flipped = False

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        new_ops: list[ast.cmpop] = []
        for op in node.ops:
            if isinstance(op, ast.Eq):
                new_ops.append(ast.NotEq())
                self._flipped = True
            elif isinstance(op, ast.NotEq):
                new_ops.append(ast.Eq())
                self._flipped = True
            elif isinstance(op, ast.Lt):
                new_ops.append(ast.GtE())
                self._flipped = True
            elif isinstance(op, ast.LtE):
                new_ops.append(ast.Gt())
                self._flipped = True
            elif isinstance(op, ast.Gt):
                new_ops.append(ast.LtE())
                self._flipped = True
            elif isinstance(op, ast.GtE):
                new_ops.append(ast.Lt())
                self._flipped = True
            elif isinstance(op, ast.In):
                new_ops.append(ast.NotIn())
                self._flipped = True
            elif isinstance(op, ast.NotIn):
                new_ops.append(ast.In())
                self._flipped = True
            else:
                new_ops.append(op)
        node.ops = new_ops
        return node


class _AndToOr(ast.NodeTransformer):
    _flipped = False

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        if not self._flipped and isinstance(node.op, ast.And):
            node.op = ast.Or()
            self._flipped = True
        return node


class _WrongId(ast.NodeTransformer):
    _replaced = False
    _from: str = ""
    _to: str = ""

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if self._replaced or not isinstance(node.value, str):
            return node
        val = node.value
        if not ID_RE.match(val):
            return node
        # Skip ultra-generic tokens
        if val.lower() in {"user", "seed", "true", "false"}:
            return node
        if "@" in val:
            local, _, domain = val.partition("@")
            new = f"wrong_{local}@{domain}"
        elif val.startswith("ORD-"):
            new = val + "-WRONG"
        elif val.startswith("p_"):
            new = "p_wrong_mutation_id"
        elif val.startswith("addr_"):
            new = "addr_wrong_mutation"
        elif val.startswith("sub_"):
            new = "sub_wrong_mutation"
        elif val.startswith("pay_"):
            new = "pay_wrong_mutation"
        elif val.startswith("ev_"):
            new = "ev_wrong_mutation"
        else:
            new = val + "_WRONG"
        self._from = val
        self._to = new
        self._replaced = True
        return ast.Constant(value=new)


class _RemoveRecipient(ast.NodeTransformer):
    _changed = False

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name in {"_sent_to", "sent_to"} and not self._changed:
            self._changed = True
            return ast.Constant(value=True)
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        # BILLING in (se.to or "").lower()  →  True
        self.generic_visit(node)
        if self._changed:
            return node
        for i, op in enumerate(node.ops):
            if not isinstance(op, ast.In):
                continue
            comparator = node.comparators[i]
            if isinstance(node.left, ast.Name) and node.left.id.upper() in {
                "BILLING",
                "USER",
                "DANA",
                "PRIYA",
            }:
                self._changed = True
                return ast.Constant(value=True)
            # email string literal in se.to
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                if "@" in node.left.value:
                    self._changed = True
                    return ast.Constant(value=True)
            _ = comparator
        return node


def _looks_like_phrase_tuple(node: ast.AST) -> bool:
    """True for email/keyword phrase lists; false for product-id inventories."""
    if not isinstance(node, (ast.Tuple, ast.List)) or not node.elts:
        return False
    strs = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    if len(strs) < 2:
        return False
    # Prefer natural-language phrases (spaces / punctuation) over bare SKUs.
    phrasey = sum(1 for s in strs if (" " in s) or any(ch in s for ch in "'.$"))
    id_like = sum(1 for s in strs if s.startswith(("p_", "ORD-", "addr_", "sub_", "pay_", "ev_")))
    return phrasey >= max(2, len(strs) // 3) and id_like == 0


class _LoosenRegex(ast.NodeTransformer):
    _changed = False

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        self.generic_visit(node)
        if self._changed:
            return node
        for t in node.targets:
            if not isinstance(t, ast.Name):
                continue
            named = t.id.upper() in {
                "FALSE_STOP",
                "_CORRECT",
                "FALSE_39",
                "TOKENS",
                "PHRASES",
                "KEYWORDS",
            } or t.id.endswith(("_TOKENS", "_PHRASES", "_KEYS", "_CORRECT"))
            if named or _looks_like_phrase_tuple(node.value):
                if isinstance(node.value, (ast.Tuple, ast.List)) and node.value.elts:
                    # Loosen: empty string matches every body via `"" in body`
                    node.value = ast.Tuple(elts=[ast.Constant(value="")], ctx=ast.Load())
                    self._changed = True
                    return node
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if self._changed:
            return node
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        if name in {"_informed_user", "_informed_user_affirmative", "_body_affirms"}:
            if len(node.args) >= 2 and _looks_like_phrase_tuple(node.args[1]):
                node.args[1] = ast.Tuple(elts=[ast.Constant(value="")], ctx=ast.Load())
                self._changed = True
        return node


class _AllowInitialState(ast.NodeTransformer):
    """Weaken filters that ignore seed/preexisting objects."""

    _changed = False

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        # source == "user"  →  True  (seeded calendar events count)
        if (
            isinstance(node.left, ast.Constant)
            and node.left.value == "user"
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
        ):
            self._changed = True
            return ast.Constant(value=True)
        if (
            len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == "user"
        ):
            # getattr(ev, "source", "") == "user"
            self._changed = True
            return ast.Constant(value=True)
        return node


class _DeleteForbidden(ast.NodeTransformer):
    _changed = False

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        if name != "Milestone":
            return node
        # Detect forbidden=True kw
        is_forb = False
        for kw in node.keywords:
            if kw.arg == "forbidden" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                is_forb = True
        if not is_forb:
            return node
        self._changed = True
        # Replace with a no-op diagnostic that never fires and is not forbidden
        return ast.Call(
            func=ast.Name(id="Milestone", ctx=ast.Load()),
            args=[
                ast.Constant(value="__deleted_forbidden__"),
                ast.Constant(value=0.0),
                ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="p")],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=ast.Constant(value=False),
                ),
            ],
            keywords=[
                ast.keyword(arg="required_for_success", value=ast.Constant(value=False)),
                ast.keyword(arg="forbidden", value=ast.Constant(value=False)),
            ],
        )


def _apply_ast_mutation(tree: ast.Module, kind: str) -> tuple[ast.Module, bool, str]:
    note = ""
    if kind == "reverse_comparison":
        tr = _ReverseCompare()
        tree = tr.visit(tree)
        return tree, tr._flipped, "flipped Eq/Lt/In-family comparators" if tr._flipped else ""
    if kind == "and_to_or":
        tr = _AndToOr()
        tree = tr.visit(tree)
        return tree, tr._flipped, "first And → Or" if tr._flipped else ""
    if kind == "wrong_id":
        tr = _WrongId()
        tree = tr.visit(tree)
        if tr._replaced:
            note = f"{tr._from!r} → {tr._to!r}"
        return tree, tr._replaced, note
    if kind == "remove_recipient":
        tr = _RemoveRecipient()
        tree = tr.visit(tree)
        return tree, tr._changed, "neutralized recipient gate" if tr._changed else ""
    if kind == "loosen_regex":
        tr = _LoosenRegex()
        tree = tr.visit(tree)
        return tree, tr._changed, "keyword/tuple loosened to empty match" if tr._changed else ""
    if kind == "allow_initial_state":
        tr = _AllowInitialState()
        tree = tr.visit(tree)
        if tr._changed:
            return tree, True, "removed source=='user' filter (seed objects count)"
        # Fallback runtime applied later
        return tree, False, ""
    if kind == "delete_forbidden":
        tr = _DeleteForbidden()
        tree = tr.visit(tree)
        return tree, tr._changed, "forbidden milestone neutered" if tr._changed else ""
    raise ValueError(kind)


def _compile_factory(tree: ast.Module, fn: Callable[[], Any], mod: Any) -> Callable[[], Any]:
    ast.fix_missing_locations(tree)
    code = compile(tree, filename=f"<mutation:{fn.__name__}>", mode="exec")
    ns = dict(vars(mod))
    exec(code, ns)  # noqa: S102 — intentional temporary suite redefinition
    new_fn = ns[fn.__name__]
    return new_fn


def _runtime_allow_initial_state(suite: Any) -> bool:
    """If AST found no seed filter, make forbidden true whenever initial_state is bound.

    This models 'preexisting binding satisfies the forbidden check' and should
    trip seed-silent / preexisting probes.
    """
    changed = False
    for m in suite.milestones:
        if not getattr(m, "forbidden", False):
            continue
        orig = m.check

        def _mut(p, o=orig):  # noqa: B023
            if getattr(p, "initial_state", None) is not None or getattr(p, "initial_world", None) is not None:
                return True
            return bool(o(p))

        m.check = _mut
        changed = True
    return changed


def _pytest_filter(task_id: str) -> str:
    n = _num(task_id)
    # Match focused tests without sucking in unrelated mNxx ids: word-ish m{n}_
    return f"m{n}_ or M{n}/ or m{n} or test_m{n}"


def _run_pytest(task_id: str) -> dict[str, Any]:
    import pytest

    n = _num(task_id)
    k_expr = f"m{n}_ or test_m{n}_"
    args = [
        "-q",
        "--tb=no",
        "-p",
        "no:cacheprovider",
        "-k",
        k_expr,
        str(ROOT / "tests" / "test_cross_app_verifiers.py"),
        str(ROOT / "tests" / "test_section2_four_part_gaps.py"),
        str(ROOT / "tests" / "test_section3_reward_hacking.py"),
        str(ROOT / "tests" / "test_vein_taxonomy.py"),
    ]
    # Extra wave/phase files if present
    for extra in (
        "tests/test_structural_implicit_wave.py",
        "tests/test_thin_vein.py",
        "tests/test_phase_d.py",
    ):
        p = ROOT / extra
        if p.exists():
            args.append(str(p))

    class _Count:
        def __init__(self) -> None:
            self.passed = 0
            self.failed = 0
            self.selected = 0
            self.errors = 0

        def pytest_runtest_logreport(self, report):  # type: ignore[no-untyped-def]
            if report.when != "call":
                return
            self.selected += 1
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1

        def pytest_collectreport(self, report):  # type: ignore[no-untyped-def]
            if report.failed:
                self.errors += 1

    counter = _Count()
    rc = pytest.main(args, plugins=[counter])
    return {
        "exit_code": int(rc),
        "passed": counter.passed,
        "failed": counter.failed,
        "selected": counter.selected,
        "collect_errors": counter.errors,
        "k_expr": k_expr,
    }


def _baseline_ok(task_id: str) -> dict[str, Any]:
    return _run_pytest(task_id)


def run_one(task_id: str, kind: str, vein: str, archetype: str) -> MutationResult:
    from server import verifiers as V
    from server.verifiers import Milestone, Probe, TaskSuite  # noqa: F401

    fn, mod = _factory_for(task_id)
    tree = _parse_factory(fn)
    mutated_tree, applicable, note = _apply_ast_mutation(tree, kind)

    runtime_fallback = False
    if kind == "allow_initial_state" and not applicable:
        runtime_fallback = True
        applicable = True
        note = "runtime: forbidden∨(initial_state bound)"

    if not applicable:
        return MutationResult(
            task_id=task_id,
            vein=vein,
            archetype=archetype,
            mutation=kind,
            applicable=False,
            caught=None,
            notes="mutation site not found in suite factory AST",
        )

    original = V.SUITE_FACTORIES[task_id]
    try:
        if runtime_fallback and kind == "allow_initial_state":
            def _factory() -> Any:
                suite = original()
                _runtime_allow_initial_state(suite)
                return suite

            V.SUITE_FACTORIES[task_id] = _factory
        else:
            new_fn = _compile_factory(mutated_tree, fn, mod)
            V.SUITE_FACTORIES[task_id] = new_fn

        stats = _run_pytest(task_id)
        failed = (stats["failed"] or 0) + (stats["collect_errors"] or 0)
        # Caught = suite screams (pytest non-zero or ≥1 failed call)
        caught = failed > 0 or stats["exit_code"] not in (0, 5)
        # exit code 5 = no tests collected — treat as not caught / finding
        if stats["exit_code"] == 5 or stats["selected"] == 0:
            return MutationResult(
                task_id=task_id,
                vein=vein,
                archetype=archetype,
                mutation=kind,
                applicable=True,
                caught=False,
                exit_code=stats["exit_code"],
                tests_failed=stats["failed"],
                tests_passed=stats["passed"],
                tests_selected=stats["selected"],
                notes=note + "; FINDING: no matching tests collected",
            )
        return MutationResult(
            task_id=task_id,
            vein=vein,
            archetype=archetype,
            mutation=kind,
            applicable=True,
            caught=bool(caught),
            exit_code=stats["exit_code"],
            tests_failed=stats["failed"],
            tests_passed=stats["passed"],
            tests_selected=stats["selected"],
            notes=note,
        )
    except Exception as exc:  # noqa: BLE001
        return MutationResult(
            task_id=task_id,
            vein=vein,
            archetype=archetype,
            mutation=kind,
            applicable=True,
            caught=True,  # compile/runtime blowup still "suite screams"
            notes=note,
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        V.SUITE_FACTORIES[task_id] = original


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure repo imports
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from trajectories.vein_taxonomy import canonical_vein

    # Verify sample veins
    for row in SAMPLE:
        cv = canonical_vein(row["task_id"])
        if cv != row["vein"]:
            row["vein_note"] = f"canonical_vein={cv} (sample tag={row['vein']})"
            row["vein"] = cv

    results: list[MutationResult] = []
    baselines: dict[str, Any] = {}

    print("== Section 2D mutation battery ==")
    print(f"sample_n={len(SAMPLE)} mutations={len(MUTATION_KINDS)}")

    for row in SAMPLE:
        tid = row["task_id"]
        print(f"\n--- baseline {tid} ---")
        try:
            baselines[tid] = _baseline_ok(tid)
            print(
                f"  selected={baselines[tid]['selected']} "
                f"failed={baselines[tid]['failed']} rc={baselines[tid]['exit_code']}"
            )
        except Exception as exc:  # noqa: BLE001
            baselines[tid] = {"error": str(exc), "exit_code": -1}
            print(f"  baseline error: {exc}")

    for row in SAMPLE:
        tid = row["task_id"]
        for kind in MUTATION_KINDS:
            print(f"mutate {tid} :: {kind} ...", flush=True)
            res = run_one(tid, kind, row["vein"], row["archetype"])
            results.append(res)
            status = (
                "N/A"
                if not res.applicable
                else ("CAUGHT" if res.caught else "SURVIVED")
            )
            print(
                f"  → {status} fail={res.tests_failed} pass={res.tests_passed} "
                f"sel={res.tests_selected} {res.notes} {res.error}",
                flush=True,
            )

    survivors = [
        r
        for r in results
        if r.applicable and r.caught is False
    ]
    caught = [r for r in results if r.applicable and r.caught]
    na = [r for r in results if not r.applicable]

    # Per-mutation summary across sample
    by_mut: dict[str, dict[str, int]] = {}
    for kind in MUTATION_KINDS:
        sub = [r for r in results if r.mutation == kind]
        by_mut[kind] = {
            "applicable": sum(1 for r in sub if r.applicable),
            "caught": sum(1 for r in sub if r.applicable and r.caught),
            "survived": sum(1 for r in sub if r.applicable and not r.caught),
            "n_a": sum(1 for r in sub if not r.applicable),
        }

    payload = {
        "schema_version": 1,
        "date": str(date.today()),
        "protocol": "docs/PRE_PUBLICATION_VALIDATION_PROTOCOL.md §2D",
        "method": {
            "mutations": list(MUTATION_KINDS),
            "application": (
                "AST rewrite of suite factory source → exec into module globals → "
                "temporary SUITE_FACTORIES patch → in-process pytest; always restored. "
                "allow_initial_state falls back to runtime forbidden∨(initial bound) "
                "when no source=='user' filter exists."
            ),
            "test_selection": (
                "pytest -k m{N}_ across test_cross_app_verifiers, "
                "test_section2_four_part_gaps, test_section3_reward_hacking, "
                "and wave files if present"
            ),
            "interpretation": (
                "CAUGHT = ≥1 failed test (or compile error). "
                "SURVIVED = applicable mutation left the selected suite green — finding."
            ),
        },
        "sample": SAMPLE,
        "baselines": baselines,
        "summary": {
            "tasks": len(SAMPLE),
            "attempts": len(results),
            "applicable": len(caught) + len(survivors),
            "caught": len(caught),
            "survived_findings": len(survivors),
            "not_applicable": len(na),
            "by_mutation": by_mut,
        },
        "survivors": [asdict(r) for r in survivors],
        "results": [asdict(r) for r in results],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")
    print(
        f"caught={len(caught)} survived={len(survivors)} n/a={len(na)} "
        f"applicable={len(caught)+len(survivors)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
