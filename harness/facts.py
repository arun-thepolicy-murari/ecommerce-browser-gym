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


def _facts_m4(world: dict, url: str) -> dict[str, Any]:
    """M4: the CHARGED order total (created in the shop) and the total shown
    in the confirmation email. The agent must carry the charged total (not
    the sticker price) into a reply."""
    facts: dict[str, Any] = {}
    orders = (world.get("shop") or {}).get("orders") or {}
    if orders:
        oid = sorted(orders)[0]
        facts["shop.order_id"] = oid
        facts["shop.order_total"] = orders[oid].get("total")
    inbox = (world.get("mail") or {}).get("inbox") or {}
    for e in inbox.values():
        if e.get("tracking_url"):                 # the shop confirmation email
            facts["mail.confirmation_total"] = e.get("amount_total")
            break
    return facts


def _facts_m5(world: dict, url: str) -> dict[str, Any]:
    """M5: which mouse the agent actually ordered (the decision outcome)."""
    facts: dict[str, Any] = {}
    mice = {"p_mouse_wireless", "p_mouse_gaming", "p_mouse_ergonomic",
            "p_mouse_mini", "p_mouse_trackpad"}
    orders = (world.get("shop") or {}).get("orders") or {}
    for o in orders.values():
        for it in o.get("items", []):
            if it.get("product_id") in mice:
                facts["shop.ordered_mouse_id"] = it["product_id"]
    return facts


def _facts_m6(world: dict, url: str) -> dict[str, Any]:
    """M6: which past order is the bigger one (from the emails) + what the
    agent actually reordered (newest order's items)."""
    facts: dict[str, Any] = {}
    inbox = (world.get("mail") or {}).get("inbox") or {}
    confs = {e.get("order_id"): e for e in inbox.values()
             if (e.get("order_id") or "").startswith("ORD-PAST")}
    if confs:
        big = max(confs.values(), key=lambda e: e.get("amount_total") or 0)
        facts["mail.bigger_order_id"] = big.get("order_id")
    orders = (world.get("shop") or {}).get("orders") or {}
    # Exclude the two pre-seeded past orders; the agent's reorder is the rest.
    new_orders = {k: o for k, o in orders.items()
                  if not (k or "").startswith("ORD-PAST")}
    if new_orders:
        newest = max(new_orders.values(), key=lambda o: o.get("placed_at", ""))
        facts["shop.reordered_items"] = sorted(
            {it.get("product_id") for it in newest.get("items", [])})
    return facts


def _facts_m7(world: dict, url: str) -> dict[str, Any]:
    """M7: the food ETA + total, and the host-gift book the agent bought."""
    facts: dict[str, Any] = {}
    forders = (world.get("food") or {}).get("orders") or {}
    if forders:
        o = next(iter(forders.values()))
        facts["food.eta"] = o.get("eta_label")
        facts["food.total"] = o.get("total")
    orders = (world.get("shop") or {}).get("orders") or {}
    for o in orders.values():
        for it in o.get("items", []):
            if (it.get("product_id") or "").startswith("p_book"):
                facts["shop.book_name"] = it.get("product_name")
    return facts


FACT_EXTRACTORS: dict[str, Callable[[dict, str], dict]] = {
    "M2/order_then_track_via_email": _facts_m2,
    "M3/dinner_then_receipt":        _facts_m3,
    "M4/order_then_reply_total":     _facts_m4,
    "M5/cheaper_mouse_from_deals":   _facts_m5,
    "M6/reorder_bigger_order":       _facts_m6,
    "M7/dinner_and_host_gift":       _facts_m7,
}


def get_fact_extractor(task_id: str) -> Callable[[dict, str], dict] | None:
    """The fact extractor for a task, or None (single-app tasks record no
    facts and skip the extra /_harness/world fetch)."""
    return FACT_EXTRACTORS.get(task_id)
