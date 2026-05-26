"""Cross-app hooks for the shop.

The shop's existing ``server.mutations`` are GymState-only and stay that way
— they know nothing about the multi-app world. The cross-app EMIT for a
placed order happens HERE, called from the checkout route after a successful
``place_order``. Centralising it (rather than inlining in the route) keeps it
DRY and lets tests reproduce the exact event the server would emit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.apps import bus

if TYPE_CHECKING:
    from server.apps.world import WorldState


def emit_shop_order_placed(world: "WorldState", order_id: str) -> None:
    """Emit ShopOrderPlaced -> a confirmation email (with a tracking link)
    lands in Mail. The tracking link points at the shop's real tracking
    route for THIS order, so 'use the tracking link' resolves correctly."""
    order = world.shop.orders.get(order_id)
    bus.emit(
        world, type="ShopOrderPlaced", source_app="shop", target_app="mail",
        payload={
            "order_id": order_id,
            "total": order.total if order is not None else 0.0,
            "tracking_url": f"/account/orders/{order_id}/track",
        },
    )


def emit_return_filed(world: "WorldState", *, return_id: str,
                      order_id: str) -> None:
    """Emit ReturnFiled — a pure TRIGGER event (target_app=shop, no subscriber).
    It lands in ``world.events`` so a scheduled relative event (e.g. a refund-
    approved email N steps later) can resolve its due step against it. The
    async refund itself is delivered by the scheduler, not here."""
    bus.emit(
        world, type="ReturnFiled", source_app="shop", target_app="shop",
        payload={"return_id": return_id, "order_id": order_id},
    )
