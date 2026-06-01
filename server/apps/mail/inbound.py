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


def deliver_market_order_confirmation(world: "WorldState",
                                      event: "WorldEvent") -> None:
    """MarketOrderPlaced -> a ValueMart order-confirmation email with the
    itemized FINAL total (subtotal - discount + delivery). The cross-retailer
    tasks check the charged total here, so it must reflect coupon + delivery,
    not the sticker sum."""
    mail = world.mail
    if mail is None:
        return
    p = event.payload
    lines = "\n".join(
        f"  {it.get('qty', 1)} x {it.get('name', '')}"
        for it in p.get("items", []))
    coupon = p.get("coupon_code")
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="orders@valuemart.com", to=mail.account_email,
        subject=f"Your ValueMart order {p.get('order_id', '')} is confirmed",
        body=(
            f"Thanks for shopping at ValueMart!\n\n"
            f"Order number: {p.get('order_id', '')}\n\n"
            f"{lines}\n\n"
            f"Subtotal: ${p.get('subtotal', 0):.2f}\n"
            + (f"Coupon ({coupon}): -${p.get('discount', 0):.2f}\n" if coupon else "")
            + f"Delivery: ${p.get('delivery_fee', 0):.2f}\n"
            f"Total charged: ${p.get('total', 0):.2f}\n"),
        received_at=f"{SEED_DATE}T12:31:00", received_label="now",
        read=False, labels=["orders"],
        order_id=p.get("order_id"), amount_total=p.get("total"))


def deliver_coupon_flip_alert(world: "WorldState", event: "WorldEvent") -> None:
    """CouponFlipAlert -> a FLASH-SALE email announcing a deeper coupon that
    FLIPS which store is cheaper (M18). Delivered ASYNCHRONOUSLY right after the
    agent commits to ShopGym, so a linear agent that's already mid-checkout must
    notice it, abandon the ShopGym plan, and switch stores. Idempotent: the
    dynamic (on-checkout) trigger and the absolute fallback both emit this, but
    only ONE email is ever added."""
    mail = world.mail
    if mail is None:
        return
    if any("coupon-flip" in (e.labels or []) for e in mail.inbox.values()):
        return                                  # already delivered — dedupe
    p = event.payload
    code = p.get("code", "")
    pct = int(round(float(p.get("percent_off", 0.0)) * 100))
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="deals@valuemart.com", to=mail.account_email,
        subject=f"FLASH SALE — {pct}% off everything at ValueMart!",
        body=(
            f"For the next hour only: use code {code} for {pct}% off your "
            f"ENTIRE ValueMart order — our biggest discount ever. Stack it on "
            f"anything in your cart. Don't miss out!\n"),
        received_at=f"{SEED_DATE}T13:15:00", received_label="now",
        read=False, labels=["coupon-flip", "deals"])


def deliver_calendar_change_alert(world: "WorldState", event: "WorldEvent") -> None:
    """CalendarChangeAlert -> a manager email that CANCELS the 2 PM meeting and
    tells the user to move the 3 PM 1:1 up to 2 PM (M22). Delivered async
    mid-task, so the agent must notice it, MOVE one event, DELETE the cancelled
    one (the destructive action agents skip -> a double-booking), and re-notify
    the guest. Idempotent: only ONE such email is ever added."""
    mail = world.mail
    if mail is None:
        return
    if any("calendar-change" in (e.labels or []) for e in mail.inbox.values()):
        return                                  # already delivered — dedupe
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="scheduling@example.com", to=mail.account_email,
        subject="Automated notice: 2 PM Team Sync cancelled",
        body=(
            "This is an automated notice from your calendar system — no reply "
            "needed.\n\n"
            "The 2 PM Team Sync has been CANCELLED. To keep your afternoon "
            "consistent, move your 3 PM 1:1 with Priya up to the freed 2 PM slot "
            "and clear the old 2 PM block so nothing is double-booked. You'll "
            "want to let Priya know her new time directly.\n"),
        received_at=f"{SEED_DATE}T13:30:00", received_label="now",
        read=False, labels=["calendar-change"])


def deliver_offsite_change_alert(world: "WorldState", event: "WorldEvent") -> None:
    """OffsiteChangeAlert -> a manager email that swaps an attendee mid-task
    (M23): Sam is out, Dana is in, and Dana can ONLY meet after 3 PM. This both
    (a) tightens the time constraint (the 1 PM slot the agent may have already
    booked is now invalid -> must move later), and (b) changes the notify target
    to Dana, who is NOT in the inbox -> the agent must COMPOSE FRESH to dana@
    (replying to this manager email -> wrong recipient, the trap). Dana's address
    is included so it is discoverable. Idempotent: only ONE such email is added."""
    mail = world.mail
    if mail is None:
        return
    if any("offsite-change" in (e.labels or []) for e in mail.inbox.values()):
        return                                  # already delivered — dedupe
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="events@example.com", to=mail.account_email,
        subject="Change to the team lunch",
        body=(
            "Update on the team lunch:\n\n"
            "Sam can no longer make it. Dana (dana@example.com) will join in "
            "Sam's place. Dana can only meet AFTER 3 PM, so move the lunch to a "
            "slot after 3 PM and email Dana directly with the final time. "
            "Thanks!\n"),
        received_at=f"{SEED_DATE}T11:30:00", received_label="now",
        read=False, labels=["offsite-change"])


def deliver_dispatch_correction(world: "WorldState", event: "WorldEvent") -> None:
    """DispatchCorrection -> a manager follow-up that CORRECTS one teammate's
    value mid-task (M25): Alex's Q3 budget is actually $21,000, not $12,000. The
    agent must relay the UPDATED figure to Alex (not the stale one), while still
    routing the other teammates' details to the right people. Idempotent."""
    mail = world.mail
    if mail is None:
        return
    if any("dispatch-correction" in (e.labels or []) for e in mail.inbox.values()):
        return                                  # already delivered — dedupe
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="manager@example.com", to=mail.account_email,
        subject="Correction — Alex's Q3 budget",
        body=(
            "One correction to my earlier note: Alex's Q3 budget is actually "
            "$21,000 (not $12,000). Please make sure Alex gets the right figure. "
            "Thanks!\n"),
        received_at=f"{SEED_DATE}T10:15:00", received_label="now",
        read=False, labels=["dispatch-correction"])


def deliver_refund_policy_update(world: "WorldState", event: "WorldEvent") -> None:
    """RefundPolicyUpdate -> the Electronics restocking fee drops 15% -> 10%
    mid-task (M31). Every electronics refund the agent computed at 15% is now
    stale and must be re-computed at the latest rate, and the grand total with
    it. The agent must relay the LATEST policy, not the first one it read.
    Idempotent on the label."""
    mail = world.mail
    if mail is None:
        return
    if any("policy-update" in (e.labels or []) for e in mail.inbox.values()):
        return
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="policy@shopgym.com", to=mail.account_email,
        subject="Policy update — electronics restocking fee",
        body=(
            "Policy update, effective immediately:\n\n"
            "The Electronics restocking fee is reduced from 15% to 10%. Please "
            "use 10% for all electronics refunds from now on. Apparel (5%) and "
            "Other (0%) are unchanged.\n\n- Refunds Policy"),
        received_at=f"{SEED_DATE}T10:30:00", received_label="now",
        read=False, labels=["policy-update"])


def deliver_sync_reschedule_1(world: "WorldState", event: "WorldEvent") -> None:
    """SyncReschedule1 -> the FIRST async availability change (M29). Two attendees'
    constraints shift so the unique valid slot moves from 2 PM to 4 PM, forcing the
    agent to MOVE the already-booked event and re-notify. De-primed sender
    (scheduling@, framed as an automated availability feed — not a person to reply
    to). Idempotent on the label."""
    mail = world.mail
    if mail is None:
        return
    if any("sync-wave1" in (e.labels or []) for e in mail.inbox.values()):
        return
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="scheduling@example.com", to=mail.account_email,
        subject="Availability update — design sync",
        body=(
            "Automated availability update (no reply needed):\n\n"
            "- Alex: my afternoon just freed up — please ignore my earlier "
            "'nothing after 3 PM' limit, I'm flexible now.\n"
            "- Priya: something came up, so I can now ONLY join after 4 PM.\n\n"
            "Please re-pick the time so it still works for everyone and let the "
            "team know.\n"),
        received_at=f"{SEED_DATE}T12:05:00", received_label="now",
        read=False, labels=["sync-wave1"])


def deliver_sync_reschedule_2(world: "WorldState", event: "WorldEvent") -> None:
    """SyncReschedule2 -> the SECOND async change (M29). Sam's window widens and a
    NEW attendee (Dana, after 5 PM only) joins, so the unique valid slot moves
    again from 4 PM to 5 PM — a second forced MOVE + re-notify, now to FOUR people
    including a fresh address. Idempotent on the label."""
    mail = world.mail
    if mail is None:
        return
    if any("sync-wave2" in (e.labels or []) for e in mail.inbox.values()):
        return
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="scheduling@example.com", to=mail.account_email,
        subject="One more change — design sync",
        body=(
            "Automated availability update (no reply needed):\n\n"
            "- Sam: good news, I can now stay as late as 6 PM.\n"
            "- Dana (dana@example.com) is joining the sync too — Dana can ONLY "
            "make it after 5 PM.\n\n"
            "Please update the time so everyone (including Dana) can attend, and "
            "confirm the final time with the whole group.\n"),
        received_at=f"{SEED_DATE}T12:20:00", received_label="now",
        read=False, labels=["sync-wave2"])


def deliver_refund_correction(world: "WorldState", event: "WorldEvent") -> None:
    """RefundCorrection -> a billing follow-up that CHANGES the refund amount mid-
    task (M30): the restocking fee was reduced, so the refund is now higher than
    the first approval email said. The agent must relay the LATEST figure (not the
    first one it read, and not the salient order total). Idempotent on the label."""
    mail = world.mail
    if mail is None:
        return
    if any("refund-correction" in (e.labels or []) for e in mail.inbox.values()):
        return
    p = event.payload
    amt = p.get("new_amount", 0.0)
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="billing@shopgym.com", to=mail.account_email,
        subject=f"Correction to your refund for {p.get('order_id', '')}",
        body=(
            f"Hi Alice,\n\nGood news — we reviewed your return for order "
            f"{p.get('order_id', '')} and reduced the restocking fee.\n\n"
            f"Your refund has been UPDATED to ${amt:.2f} (this replaces the "
            f"amount in our earlier email). Please use this corrected figure.\n\n"
            f"- ShopGym Billing"),
        received_at=f"{SEED_DATE}T15:10:00", received_label="now",
        read=False, labels=["refund-correction"],
        order_id=p.get("order_id"), amount_total=amt)


def deliver_project_cancellation(world: "WorldState", event: "WorldEvent") -> None:
    """ProjectCancelled -> a manager email that cancels a project and instructs
    the agent to delete ALL its meetings EXCEPT one repurposed exception that must
    be KEPT (M26). Delivered async (step 5), so the agent must notice it arrive,
    then delete EXACTLY the right meetings — not the kept exception, not a same-day
    decoy from another project. The verifier's target rule ('phoenix' in title AND
    not 'retro') is kept in lockstep with this body. Idempotent on the label."""
    mail = world.mail
    if mail is None:
        return
    if any("project-cancelled" in (e.labels or []) for e in mail.inbox.values()):
        return                                  # already delivered — dedupe
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="manager@example.com", to=mail.account_email,
        subject="Project Phoenix cancelled — please clear my calendar",
        body=(
            "Project Phoenix has been cancelled, effective immediately.\n\n"
            "Please remove ALL Phoenix meetings from tomorrow's calendar so my "
            "day is clear of it.\n\n"
            "ONE EXCEPTION: keep the 'Phoenix Retro' at 3:00 PM — it has been "
            "repurposed into our Q3 Planning sync, so that meeting STAYS on the "
            "calendar. Everything else with Phoenix in the name should go.\n\n"
            "Please don't touch any of my other meetings. Thanks!\n"),
        received_at=f"{SEED_DATE}T10:30:00", received_label="now",
        read=False, labels=["project-cancelled"])


def deliver_budget_raise(world: "WorldState", event: "WorldEvent") -> None:
    """RefundBudgetRaised -> a manager email that RAISES today's refund budget
    mid-task (M27): $200 -> $300. This moves the running-total cutoff later, so
    several requests the agent already deferred now fit and must be approved. The
    agent must notice the update, use the NEW number, and re-evaluate — the async
    self-invalidation that linear agents skip. Idempotent on the label."""
    mail = world.mail
    if mail is None:
        return
    if any("budget-raise" in (e.labels or []) for e in mail.inbox.values()):
        return                                  # already delivered — dedupe
    p = event.payload
    newb = int(p.get("new_budget", 300))
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="manager@example.com", to=mail.account_email,
        subject="Update — today's refund budget raised",
        body=(
            f"Good news — finance just bumped today's refund budget UP to ${newb}.\n\n"
            f"Please use ${newb} as the cap from now on (it REPLACES the earlier "
            f"$200). Keep approving eligible requests oldest-first until the "
            f"approved total would exceed ${newb}, then defer the rest as before.\n"),
        received_at=f"{SEED_DATE}T10:30:00", received_label="now",
        read=False, labels=["budget-raise"])


def deliver_delivery_delayed(world: "WorldState", event: "WorldEvent") -> None:
    """DeliveryDelayed -> a 'your delivery is running late' email with a NEW
    ETA. Delivered ASYNCHRONOUSLY by the scheduler a few steps AFTER the agent
    places the food order, so the agent's original plan (calendar reminder +
    guest note at the FIRST ETA) is now stale: it must move the reminder to the
    new ETA, NOT keep the old one, and tell the guest the new time."""
    mail = world.mail
    if mail is None:
        return
    p = event.payload
    new_eta = p.get("new_eta_label", "")
    old_eta = p.get("old_eta_label", "")
    eid = mail.new_id()
    mail.inbox[eid] = Email(
        id=eid, sender="delivery@foodapp.com", to=mail.account_email,
        subject=f"Update: your {p.get('restaurant', '')} delivery is running late",
        body=(
            f"Sorry — your order from {p.get('restaurant', '')} is running "
            f"behind.\n\n"
            f"  Original ETA: {old_eta}\n"
            f"  NEW ETA:      {new_eta}\n\n"
            f"Thanks for your patience.\n"
        ),
        received_at=f"{SEED_DATE}T18:45:00", received_label="now",
        read=False, labels=["delivery"],
        eta=new_eta,
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
