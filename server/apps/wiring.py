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
