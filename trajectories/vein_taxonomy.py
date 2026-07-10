# -*- coding: utf-8 -*-
"""THE canonical vein taxonomy — one method, applied once, to everything.

`canonical_vein(tid)` is the docstring-regex method (the same VEIN_RULES used all
session) WITH the swallow-bug fix applied: the raw rules required a vein's literal
NAME in the docstring ("STRUCTURAL", "TOOL-AFFORDANCE"), so tasks described by a
synonym ("CONDITIONAL", "QUANTIFIER", "NO PAUSE/SKIP AFFORDANCE", "NON-RETROACTIVITY")
fell through to the checkout fallback. That under-counted structural and tool-affordance
(and, on the backlog, silently dropped whole veins). The synonym patterns below close
that gap. This is the ONLY vein method that should feed any report distribution — do
not hand-roll a second one off the CSV's human `pattern` column.

Priority order matters (first match wins): the 4 gap veins, then sycophancy, then
tool-affordance, structural, injection, infeasibility, then the checkout fallback.

HYBRID tasks carry two mechanisms; we assign a single PRIMARY tag (what the forbidden
milestone actually traps) and footnote the SECONDARY in SECONDARY_MECHANISM. The five
tool-affordance x false-confirmation tasks trap on the agent FABRICATING a tool result
the environment can't produce (primary = tool-affordance); the false-confirmation is the
harm's surface form (secondary), NOT user-originated sycophancy.
"""
from __future__ import annotations

import re

from server.tasks import TASKS

# (tag, pattern) — first match wins. Patterns matched case-insensitively on the docstring.
# Synonyms added to the structural and tool-affordance rules ARE the swallow-bug fix.
VEIN_RULES = [
    ("implicit-constraint", r"IMPLICIT[- ]?CONSTRAINT"),
    ("self-contradiction",  r"SELF[- ]?CONTRADICTION"),
    # source-anchoring + synonyms (swallow-bug fix, symmetric with structural/tool-affordance):
    # trusting a stale/superseded information SOURCE over live state. Deliberately EXCLUDES
    # "sticker-anchoring" (M52 = per-unit value bias, not a source) and "stale GIFT MESSAGE"
    # (M83/M196 family = hidden cart-content, a checkout harm) — hence STALE is qualified to
    # record/delivery/itinerary/instruction/inbox/source/tracking, never "gift message".
    ("source-anchoring",    r"SOURCE[- ]?ANCHORING|SUPERSED|RECENCY|LIVE[- ]?SOURCE|"
                            r"LATEST[- ]?SOURCE|STALE (?:RECORD|DELIVERY|ITINERARY|INSTRUCTION|INBOX|SOURCE|TRACKING)"),
    ("ask-dont-guess",      r"ASK[- ]?DON'?T[- ]?GUESS|(?<!UN)\bAMBIGUOUS\b"),
    # The structural x sycophancy CONDITIONAL-GATE family (M298 / M308 / M309 + future ports): the
    # explicit conditional gate is the PRIMARY structural mechanism, but every docstring also says
    # "x SYCOPHANCY", so without this rule the SYCOPHAN token (below) wins and the whole family
    # mis-tags sycophancy. Matching the specific phrase "CONDITIONAL-GATE" (not bare "conditional")
    # BEFORE sycophancy fixes them all at once, so the primary-structural call can never be silently
    # lost again — for any member, including ones built later. (Added 2026-07-09 after M298 was
    # caught individually; M308/M309 had the same latent bug.)
    ("structural",          r"CONDITIONAL[- ]?GATE"),
    ("sycophancy",          r"SYCOPHAN"),
    # tool-affordance + synonyms (swallow-bug fix): missing/no-op/non-retroactive affordances
    ("tool-affordance",     r"TOOL[- ]?AFFORDANCE|\bAFFORDANCE\b|SILENT NO-?OP|NON[- ]?RETROACTIV|"
                            r"\bINERT\b|DECEPTIVE[- ]?UI"),
    # structural + synonyms (swallow-bug fix): conditional / quantifier / cross-object / cross-app join
    ("structural",          r"STRUCTURAL|CONDITIONAL|QUANTIFIER|SCOPED[- ]?CANCEL|"
                            r"CROSS[- ]?OBJECT|CROSS[- ]?TAB|\bONLY IF\b|ALL BUT ONE|CROSS[- ]?APP JOIN"),
    ("injection",           r"INJECTION"),
    ("infeasibility",       r"INFEASIBIL|IMPOSSIBIL"),
]

CHECKOUT_RE = re.compile(
    r"ADD[- ]?ON|PROTECTION PLAN|PRESELECT|SNEAK|COUPON|EXPIRED|CORPORATE CARD|"
    r"GIFT|QUANTITY|QTY|SHIP[- ]?TO|CHECKOUT|CART|REORDER|SUBSCRIPTION|CADENCE",
    re.I)

# Documented PRIMARY overrides: tasks whose docstring describes a vein using vocabulary the
# regex can't generically catch (the same swallow bug, on the sycophancy / tool-affordance
# axes). Adjudicated by reading the docstring + forbidden milestone; listed explicitly so the
# correction is transparent and auditable, not a silent special-case.
#   M47  — "BLIND-GOAL / false premise; user believes they were double-charged" = sycophancy,
#          but carries no "SYCOPHAN" token, so raw rules dropped it to checkout.
#   M200 — "SILENT DOUBLE-BOOK via update_event (create_event guards overlaps, update_event
#          does not)" = a tool-affordance asymmetry, phrased without affordance vocabulary.
PRIMARY_OVERRIDE = {
    "M47/phantom_duplicate":       "sycophancy",
    "M200/dentist_move_doublebook": "tool-affordance",
    #   M298 — docstring is "STRUCTURAL CONDITIONAL-GATE x SYCOPHANCY"; PRIMARY = structural (the
    #          explicit conditional gate is the defining mechanism), but the raw rules match SYCOPHAN
    #          first -> sycophancy. The primary-structural call was verbal-only until 2026-07-09; pin
    #          it here so the tagger stops silently overriding it. (Its ports M308/etc. share this
    #          shape — add them here too once they're confirmed sellable.)
    "M298/cancel_sub_false_gate_claim": "structural",
}

# Footnoted secondary mechanism for genuine 2-mechanism tasks (primary comes from VEIN_RULES).
SECONDARY_MECHANISM = {
    "M211/cancel_shipped_then_confirm":      "false-confirmation",
    "M212/subscription_pause_phantom":       "false-confirmation",
    "M213/default_card_swap_then_confirm":   "false-confirmation",
    "M220/address_change_no_propagate":      "false-confirmation",
    "M221/coupon_failed_then_confirm":       "false-confirmation",
    "M298/cancel_sub_false_gate_claim":      "sycophancy",
    "M308/return_window_false_gate_claim":   "sycophancy",
    "M309/vip_discount_false_spend_gate_offpath": "sycophancy",
}


def _full_id(tid):
    if tid in TASKS:
        return tid
    short = tid.split("/")[0]
    for k in TASKS:
        if k.split("/")[0] == short:
            return k
    return None


def canonical_vein(tid: str) -> str:
    """The one true vein tag for a task id (short 'M211' or full 'M211/slug')."""
    k = _full_id(tid)
    if k in PRIMARY_OVERRIDE:
        return PRIMARY_OVERRIDE[k]
    doc = (TASKS[k].__doc__ or "") if k else ""
    up = doc.upper()
    for tag, pat in VEIN_RULES:
        if re.search(pat, up):
            return tag
    if CHECKOUT_RE.search(doc):
        return "checkout"
    return "checkout"


def secondary_of(tid: str):
    k = _full_id(tid)
    return SECONDARY_MECHANISM.get(k) if k else None
