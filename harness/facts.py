"""Per-task fact extractors for the per-step facts layer.

A fact extractor reads the multi-app world snapshot (``/_harness/world``) +
the active tab URL and returns the environment-truth facts that are VISIBLE
or were just CREATED at this step, namespaced by app. The harness records
them in ``StepRecord.facts_visible_or_created``.

Why this matters: the failure harvester (commit 8) compares the facts the
environment SHOWED the agent against the values the agent later acted on.
That is how "the order id was on screen at step 4 but the agent tracked a
different id at step 7" becomes a detectable, recurring causal chain rather
than a vague "wrong answer".

Extractors must be pure + defensive (the world dict may be partially filled
mid-episode); they are wrapped in try/except by the harness, but should not
rely on that.
"""

from __future__ import annotations

from typing import Any, Callable


def _facts_m2(world: dict, url: str) -> dict[str, Any]:
    """M2: the order id (created in the shop) and the tracking link (shown in
    the confirmation email). The agent must carry these from Mail back to the
    shop tracking page."""
    facts: dict[str, Any] = {}
    orders = (world.get("shop") or {}).get("orders") or {}
    if orders:
        facts["shop.order_id"] = sorted(orders)[0]
    inbox = (world.get("mail") or {}).get("inbox") or {}
    for e in inbox.values():
        if e.get("tracking_url"):
            facts["mail.order_id"] = e.get("order_id")
            facts["mail.tracking_url"] = e.get("tracking_url")
            break
    return facts


def _facts_m3(world: dict, url: str) -> dict[str, Any]:
    """M3: the food order id + its total (created in Food) and the receipt
    total/ETA (shown in the receipt email)."""
    facts: dict[str, Any] = {}
    forders = (world.get("food") or {}).get("orders") or {}
    if forders:
        oid = sorted(forders)[0]
        facts["food.order_id"] = oid
        facts["food.total"] = forders[oid].get("total")
    inbox = (world.get("mail") or {}).get("inbox") or {}
    for e in inbox.values():
        if "receipts" in (e.get("labels") or []):
            facts["mail.receipt_order_id"] = e.get("order_id")
            facts["mail.receipt_total"] = e.get("amount_total")
            facts["mail.eta"] = e.get("eta")
            break
    return facts


FACT_EXTRACTORS: dict[str, Callable[[dict, str], dict]] = {
    "M2/order_then_track_via_email": _facts_m2,
    "M3/dinner_then_receipt":        _facts_m3,
}


def get_fact_extractor(task_id: str) -> Callable[[dict, str], dict] | None:
    """The fact extractor for a task, or None (single-app tasks record no
    facts and skip the extra /_harness/world fetch)."""
    return FACT_EXTRACTORS.get(task_id)
