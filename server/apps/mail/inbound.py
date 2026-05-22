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
