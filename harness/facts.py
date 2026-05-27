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


def _facts_m8(world: dict, url: str) -> dict[str, Any]:
    """M8: the aggregate shop-orders total (the branch condition) + the
    most-expensive order id (the superlative the agent must pick)."""
    facts: dict[str, Any] = {}
    inbox = (world.get("mail") or {}).get("inbox") or {}
    confs = {e.get("order_id"): e for e in inbox.values()
             if (e.get("order_id") or "").startswith("ORD-P")}
    if confs:
        facts["mail.shop_orders_total"] = round(
            sum((e.get("amount_total") or 0) for e in confs.values()), 2)
        big = max(confs.values(), key=lambda e: e.get("amount_total") or 0)
        facts["mail.most_expensive_order_id"] = big.get("order_id")
    return facts


def _facts_m9(world: dict, url: str) -> dict[str, Any]:
    """M9: the GATE (is tomorrow evening free?) the branch hinges on, plus the
    food ETA and whether the agent created a calendar event. Recording
    ``calendar.evening_free`` is what lets the harvester catch "the calendar
    said busy but the agent ordered anyway"."""
    facts: dict[str, Any] = {}
    cal = world.get("calendar") or {}
    tomorrow = cal.get("tomorrow")
    evs = cal.get("events") or {}
    if tomorrow:
        # Mirror CalendarState.is_free over the 18:00-23:00 evening window.
        evening_busy = any(
            e.get("day") == tomorrow and e.get("start", "") < "23:00"
            and "18:00" < e.get("end", "")
            for e in evs.values())
        facts["calendar.evening_free"] = not evening_busy
    forders = (world.get("food") or {}).get("orders") or {}
    if forders:
        facts["food.eta"] = next(iter(forders.values())).get("eta_label")
    facts["calendar.user_event_created"] = any(
        e.get("source") == "user" for e in evs.values())
    return facts


def _facts_m10(world: dict, url: str) -> dict[str, Any]:
    """M10 source-of-truth conflict: record BOTH signals the agent must
    reconcile. ``calendar.evening_free`` is always True here (the salient
    'go' signal); ``mail.alex_available`` is False on conflict seeds. The gap
    between the two IS the task — recording both is what lets the harvester
    catch 'ordered even though Alex's email said no'."""
    facts: dict[str, Any] = {}
    cal = world.get("calendar") or {}
    tomorrow = cal.get("tomorrow")
    evs = cal.get("events") or {}
    if tomorrow:
        evening_busy = any(
            e.get("day") == tomorrow and e.get("start", "") < "23:00"
            and "18:00" < e.get("end", "")
            for e in evs.values())
        facts["calendar.evening_free"] = not evening_busy
    inbox = (world.get("mail") or {}).get("inbox") or {}
    for e in inbox.values():
        if "alex@" in (e.get("sender") or "").lower():
            body = (e.get("body") or "").lower()
            conflict = any(w in body for w in
                           ("another day", "can't make", "won't land",
                            "can't do dinner", "reschedule"))
            facts["mail.alex_available"] = not conflict
            break
    return facts


def _facts_m11(world: dict, url: str) -> dict[str, Any]:
    """M11 reconciliation: the QUALIFYING set (orders >$100 & not shipped, the
    env truth the agent must match) and what it has CANCELLED so far (from sent
    emails). The gap between them is the failure — a missed qualifying cancel
    or a cancelled trap."""
    facts: dict[str, Any] = {}
    mail = world.get("mail") or {}
    inbox = mail.get("inbox") or {}
    sent = mail.get("sent") or {}
    all_orders: dict[str, tuple] = {}
    for e in inbox.values():
        oid = e.get("order_id") or ""
        if oid.startswith("ORD-"):
            total = e.get("amount_total") or 0.0
            shipped = "status: shipped" in (e.get("body") or "").lower()
            all_orders[oid] = (total, shipped)
    facts["mail.qualifying_orders"] = sorted(
        oid for oid, (t, s) in all_orders.items() if t > 100.0 and not s)
    facts["mail.cancelled_orders"] = sorted(
        oid for oid in all_orders
        if any(oid in ((se.get("subject") or "") + (se.get("body") or ""))
               and "cancel" in (se.get("body") or "").lower()
               for se in sent.values()))
    return facts


def _facts_m13(world: dict, url: str) -> dict[str, Any]:
    """M13 conjunctive boundary-trap: qualifying = CHARGED (amount_total) > $50
    AND not shipped AND not gift; plus what's been cancelled. The gap reveals
    the failure (cancelled a charged<=$50 'subtotal trap' / the gift / a
    shipped order, or missed a required cancel)."""
    facts: dict[str, Any] = {}
    mail = world.get("mail") or {}
    inbox = mail.get("inbox") or {}
    sent = mail.get("sent") or {}
    all_orders: dict[str, tuple] = {}
    for e in inbox.values():
        oid = e.get("order_id") or ""
        if oid.startswith("ORD-"):
            charged = e.get("amount_total") or 0.0
            body = (e.get("body") or "").lower()
            shipped = "status: shipped" in body
            is_gift = "gift note" in body
            all_orders[oid] = (charged, shipped, is_gift)
    facts["mail.qualifying_orders"] = sorted(
        oid for oid, (c, s, g) in all_orders.items()
        if c > 50.0 and not s and not g)
    facts["mail.cancelled_orders"] = sorted(
        oid for oid in all_orders
        if any(oid in ((se.get("subject") or "") + (se.get("body") or ""))
               and "cancel" in (se.get("body") or "").lower()
               for se in sent.values()))
    return facts


def _facts_m14(world: dict, url: str) -> dict[str, Any]:
    """M14 async refund — 4-level facts so a failure is unambiguously the
    agent's: ``delivered`` (the refund email exists), ``visible`` (the agent is
    ON its message page right now), and ``mail.refund_amount`` recorded ONLY
    when the email is READ (so coverage = the agent actually opened it, never a
    fact it couldn't have seen). 'used' is checked by the verifier on the
    reply."""
    import re
    facts: dict[str, Any] = {}
    inbox = (world.get("mail") or {}).get("inbox") or {}
    for e in inbox.values():
        sender = (e.get("sender") or "").lower()
        if "support@" in sender and e.get("read"):
            # The RMA carried IN from the support email (recorded only when the
            # agent has actually opened it).
            m = re.search(r"RMA-\d+", e.get("body", "") or "")
            if m:
                facts["mail.rma_code"] = m.group(0)
        if "refunds@" in sender:
            facts["mail.refund_delivered"] = True
            if e.get("id") and e["id"] in (url or ""):
                facts["mail.refund_visible"] = e.get("amount_total")
            if e.get("read"):
                facts["mail.refund_amount"] = e.get("amount_total")
    return facts


def _facts_m15(world: dict, url: str) -> dict[str, Any]:
    """M15 async price-watch — 4-level facts. ``alert_delivered`` (env truth),
    ``alert_visible`` (on the alert's message page now), and the alerted product
    + new price recorded ONLY when the alert email is READ, so coverage = the
    agent actually opened it. 'used' (bought that mouse at that price) is checked
    by the verifier on the placed order."""
    facts: dict[str, Any] = {}
    inbox = (world.get("mail") or {}).get("inbox") or {}
    for e in inbox.values():
        if "price-drop" not in (e.get("labels") or []):
            continue
        facts["mail.alert_delivered"] = True
        if e.get("id") and e["id"] in (url or ""):
            facts["mail.alert_visible"] = e.get("product_id")
        if e.get("read"):
            facts["mail.alerted_product_id"] = e.get("product_id")
            facts["mail.alerted_new_price"] = e.get("amount_total")
    return facts


def _facts_m16(world: dict, url: str) -> dict[str, Any]:
    """M16 async dinner-delay — 4-level facts. The first ETA (from the food
    order), the delay-notice delivery/visible/read levels (new ETA recorded only
    when READ), and the agent's current calendar reminder time + count (the
    negative-action signal: count==1 at the new time is correct, count>1 is the
    over-keep failure). 'used' is checked by the verifier on final state."""
    facts: dict[str, Any] = {}
    for o in ((world.get("food") or {}).get("orders") or {}).values():
        facts["food.initial_eta"] = o.get("eta_label")
    for e in ((world.get("mail") or {}).get("inbox") or {}).values():
        if "delivery" not in (e.get("labels") or []):
            continue
        facts["mail.delay_delivered"] = True
        if e.get("id") and e["id"] in (url or ""):
            facts["mail.delay_visible"] = e.get("eta")
        if e.get("read"):
            facts["mail.new_eta"] = e.get("eta")
    user_evs = [ev for ev in ((world.get("calendar") or {}).get("events") or {}).values()
                if ev.get("source") == "user"]
    if user_evs:
        facts["calendar.user_event_time"] = user_evs[0].get("start")
        facts["calendar.user_event_count"] = len(user_evs)
    return facts


def _facts_m19(world: dict, url: str) -> dict[str, Any]:
    """M19 coupon minefield — which coupon codes the agent saw (recorded when
    the email is READ), separating the valid VALUE10 from the expired decoy
    VALUEMART50. 'used' (buy with VALUE10 under budget) is checked by the
    verifier."""
    import re
    facts: dict[str, Any] = {}
    for e in ((world.get("mail") or {}).get("inbox") or {}).values():
        if "deals@valuemart.com" not in (e.get("sender") or "").lower():
            continue
        if not e.get("read"):
            continue
        m = re.search(r"VALUE\w+", e.get("body", "") or "")
        if not m:
            continue
        code = m.group(0)
        if code == "VALUE10":
            facts["mail.valid_coupon_code"] = "VALUE10"
        elif code == "VALUEMART50":
            facts["mail.expired_coupon_seen"] = "VALUEMART50"
    return facts


def _facts_m18(world: dict, url: str) -> dict[str, Any]:
    """M18 async coupon-flip — the flip email's delivery (env truth) + the new
    coupon code recorded ONLY when the agent READS the flash-sale email (so
    coverage = did it actually notice the mid-task flip). 'used' (buy ValueMart
    with VALUEMART30) is checked by the verifier."""
    import re
    facts: dict[str, Any] = {}
    for e in ((world.get("mail") or {}).get("inbox") or {}).values():
        if "coupon-flip" not in (e.get("labels") or []):
            continue
        facts["mail.flip_delivered"] = True
        if e.get("read"):
            m = re.search(r"VALUEMART\d+", e.get("body", "") or "")
            if m:
                facts["mail.flip_coupon_code"] = m.group(0)
    return facts


def _facts_m17(world: dict, url: str) -> dict[str, Any]:
    """M17 cross-retailer — the prices the agent must compare across the two
    stores + the emailed coupon (recorded when its email is READ). 'used' (buy
    the cheaper store with the coupon) is checked by the verifier."""
    import re
    facts: dict[str, Any] = {}
    sprod = ((world.get("shop") or {}).get("products") or {}).get("p_monitor_24")
    if sprod is not None:
        facts["shop.monitor_price"] = sprod.get("base_price", sprod.get("price"))
    mprod = ((world.get("market") or {}).get("products") or {}).get("vm_monitor_24")
    if mprod is not None:
        facts["market.monitor_price"] = mprod.get("price")
    for e in ((world.get("mail") or {}).get("inbox") or {}).values():
        if "valuemart" in (e.get("sender") or "").lower() and e.get("read"):
            mm = re.search(r"VALUE\d+", e.get("body", "") or "")
            if mm:
                facts["mail.coupon_code"] = mm.group(0)
    return facts


FACT_EXTRACTORS: dict[str, Callable[[dict, str], dict]] = {
    "M2/order_then_track_via_email": _facts_m2,
    "M3/dinner_then_receipt":        _facts_m3,
    "M4/order_then_reply_total":     _facts_m4,
    "M5/cheaper_mouse_from_deals":   _facts_m5,
    "M6/reorder_bigger_order":       _facts_m6,
    "M7/dinner_and_host_gift":       _facts_m7,
    "M8/spending_audit_branch":      _facts_m8,
    "M9/calendar_gated_dinner":      _facts_m9,
    "M10/dinner_source_conflict":    _facts_m10,
    "M11/cancel_unshipped_over_100": _facts_m11,
    "M13/order_cleanup_audit":       _facts_m13,
    "M14/return_then_refund":        _facts_m14,
    "M15/inbox_price_watch":         _facts_m15,
    "M16/coordinated_dinner_delay":  _facts_m16,
    "M17/cross_retailer_cheaper":    _facts_m17,
    "M18/async_coupon_flip":         _facts_m18,
    "M19/coupon_minefield":          _facts_m19,
}


def get_fact_extractor(task_id: str) -> Callable[[dict, str], dict] | None:
    """The fact extractor for a task, or None (single-app tasks record no
    facts and skip the extra /_harness/world fetch)."""
    return FACT_EXTRACTORS.get(task_id)
