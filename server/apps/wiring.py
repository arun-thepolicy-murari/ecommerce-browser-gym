"""Register the default cross-app event subscribers.

Called once at server startup (from ``server.main``). Tests register the
subscribers they need explicitly (after clearing the registry), so the
production wiring here never interferes with test isolation.
"""

from __future__ import annotations

from server.apps import bus
from server.apps.mail import inbound


def register_default_subscribers() -> None:
    bus.subscribe("FoodOrderPlaced", inbound.deliver_food_receipt)
    bus.subscribe("ShopOrderPlaced", inbound.deliver_shop_order_confirmation)
    # Async deliveries fired by the scheduler (server.apps.scheduler):
    bus.subscribe("RefundApproved", inbound.deliver_refund_approved)
