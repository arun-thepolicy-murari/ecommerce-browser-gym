"""Inbound deliveries INTO Mail, triggered by OTHER apps' events.

Each function here is a bus subscriber: it turns an event payload from
another app into an :class:`Email` in MailState. These are the ONLY way
another app's activity writes Mail. That keeps every cross-app effect
auditable (one logged ``WorldEvent`` per delivery) and keeps the producing
app's mutation free of any Mail access — so "the receipt never arrived"
(no delivered event) stays distinguishable from "the agent never opened
it" (delivered event, email unread).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.apps.mail.state import Email, SEED_DATE

if TYPE_CHECKING:
    from server.apps.bus import WorldEvent
    from server.apps.world import WorldState


def deliver_food_receipt(world: "WorldState", event: "WorldEvent") -> None:
    """FoodOrderPlaced -> a receipt email (with total + ETA) in the inbox."""
    mail = world.mail
    if mail is None:
        return
    p = event.payload
    lines = "\n".join(
        f"  {it.get('qty', 1)} x {it.get('name', '')}"
        for it in p.get("items", [])
    )
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="receipts@foodapp.com", to=mail.account_email,
        subject=f"Your {p.get('restaurant', '')} order is on the way",
        body=(
            f"Thanks for your order from {p.get('restaurant', '')}!\n\n"
            f"{lines}\n\n"
            f"Subtotal: ${p.get('subtotal', 0):.2f}\n"
            f"Delivery: ${p.get('delivery_fee', 0):.2f}\n"
            f"Total charged: ${p.get('total', 0):.2f}\n\n"
            f"Estimated arrival: {p.get('eta', '')}\n"
        ),
        received_at=f"{SEED_DATE}T18:31:00", received_label="now",
        read=False, labels=["receipts"],
        order_id=p.get("order_id"), amount_total=p.get("total"),
        eta=p.get("eta"),
    )


def deliver_shop_order_confirmation(world: "WorldState",
                                    event: "WorldEvent") -> None:
    """ShopOrderPlaced -> an order-confirmation email with a tracking link.
    (The shop emits this in commit 4; registering the subscriber now is
    harmless — with no emitter it simply never fires.)"""
    mail = world.mail
    if mail is None:
        return
    p = event.payload
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="orders@shopgym.com", to=mail.account_email,
        subject=f"Your ShopGym order {p.get('order_id', '')} is confirmed",
        body=(
            "Thanks for your order!\n\n"
            f"Order number: {p.get('order_id', '')}\n"
            f"Total: ${p.get('total', 0):.2f}\n\n"
            "Use the tracking link below to see where your package is.\n"
        ),
        received_at=f"{SEED_DATE}T12:05:00", received_label="now",
        read=False, labels=["orders"],
        order_id=p.get("order_id"), amount_total=p.get("total"),
        tracking_url=p.get("tracking_url"),
    )


def deliver_price_drop_alert(world: "WorldState", event: "WorldEvent") -> None:
    """PriceDropAlert -> a deals email naming ONE product + its NEW price.
    Delivered ABSOLUTELY by the scheduler (e.g. step 4) WHILE the agent waits
    on the inbox. Its pair, ShopPriceChanged, drops the same product's price in
    the shop at the same step, so the new price is genuinely obtainable and an
    agent that bought earlier is provably stale. The agent must read which
    product + new price off THIS email and buy that exact one at the new
    price."""
    mail = world.mail
    if mail is None:
        return
    p = event.payload
    name = p.get("product_name", "")
    newp = p.get("new_price", 0.0)
    oldp = p.get("old_price", 0.0)
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="alerts@shopgym.com", to=mail.account_email,
        subject=f"Price drop: {name} is now ${newp:.2f}",
        body=(
            f"Good news — a item on your watchlist just dropped in price.\n\n"
            f"{name}\n"
            f"  Was: ${oldp:.2f}\n"
            f"  Now: ${newp:.2f}\n\n"
            f"This price is live in the shop now. Grab it while it lasts!\n"
        ),
        received_at=f"{SEED_DATE}T13:00:00", received_label="now",
        read=False, labels=["price-drop"],
        product_id=p.get("product_id"), amount_total=newp,
    )


def deliver_refund_approved(world: "WorldState", event: "WorldEvent") -> None:
    """RefundApproved -> a refund-approved email. Delivered ASYNCHRONOUSLY by
    the scheduler a few steps AFTER the agent files the return — so the agent
    must notice it arrive (e.g. by switching to the Mail tab) and act on the
    EXACT refund amount (which is the order amount minus a restocking fee, NOT
    the sticker price)."""
    mail = world.mail
    if mail is None:
        return
    p = event.payload
    amt = p.get("refund_amount", 0.0)
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="refunds@shopgym.com", to=mail.account_email,
        subject=f"Your refund for {p.get('order_id', '')} is approved",
        body=(
            f"Good news — your return for order {p.get('order_id', '')} has "
            f"been approved.\n\n"
            f"Refund amount: ${amt:.2f}\n"
            f"Refund method: {p.get('refund_method', 'original payment')}\n\n"
            f"Please REPLY to this email to confirm the refund amount and that "
            f"the item is on its way back.\n"
        ),
        received_at=f"{SEED_DATE}T14:20:00", received_label="now",
        read=False, labels=["refunds"],
        order_id=p.get("order_id"), amount_total=amt,
    )
