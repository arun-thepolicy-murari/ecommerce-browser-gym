"""Register the default cross-app event subscribers.

Called once at server startup (from ``server.main``). Tests register the
subscribers they need explicitly (after clearing the registry), so the
production wiring here never interferes with test isolation.
"""

from __future__ import annotations

from server.apps import bus, shop_hooks
from server.apps.mail import inbound


def register_default_subscribers() -> None:
    bus.subscribe("FoodOrderPlaced", inbound.deliver_food_receipt)
    bus.subscribe("ShopOrderPlaced", inbound.deliver_shop_order_confirmation)
    # ValueMart (2nd e-commerce store) order -> confirmation email in Mail.
    bus.subscribe("MarketOrderPlaced", inbound.deliver_market_order_confirmation)
    # Async deliveries fired by the scheduler (server.apps.scheduler):
    bus.subscribe("RefundApproved", inbound.deliver_refund_approved)
    # Paired price-drop (M15): the email lands in Mail AND the shop price
    # actually drops — same step, two targets.
    bus.subscribe("PriceDropAlert", inbound.deliver_price_drop_alert)
    bus.subscribe("ShopPriceChanged", shop_hooks.apply_shop_price_change)
    # Async delivery-delay notice (M16): pushes the ETA into a later slot.
    bus.subscribe("DeliveryDelayed", inbound.deliver_delivery_delayed)
    # Async coupon-flip (M18): a deeper coupon arrives mid-checkout and flips
    # which store is cheaper. (ShopCheckoutReached is a pure trigger -> no
    # subscriber; the scheduler keys the flip email off it.)
    bus.subscribe("CouponFlipAlert", inbound.deliver_coupon_flip_alert)
    # Async calendar overwrite (M22): a manager email cancels the 2 PM meeting
    # and moves the 3 PM 1:1 up — forcing a MOVE + a destructive DELETE + re-notify.
    bus.subscribe("CalendarChangeAlert", inbound.deliver_calendar_change_alert)
    # Async offsite attendee swap (M23): Sam out, Dana in (after 3 PM only) —
    # tightens the time constraint + changes the notify target to a fresh address.
    bus.subscribe("OffsiteChangeAlert", inbound.deliver_offsite_change_alert)
    # Async dispatch correction (M25): one teammate's value is corrected mid-task,
    # so the agent must relay the updated figure to the right person.
    bus.subscribe("DispatchCorrection", inbound.deliver_dispatch_correction)
    # Async project cancellation (M26): clear all of a project's meetings EXCEPT
    # one repurposed exception — a destructive exact-set purge with a kept event.
    bus.subscribe("ProjectCancelled", inbound.deliver_project_cancellation)
    # Async refund-budget raise (M27): $200 -> $300 mid-task moves the running-
    # total cutoff, forcing re-evaluation of already-deferred requests.
    bus.subscribe("RefundBudgetRaised", inbound.deliver_budget_raise)
