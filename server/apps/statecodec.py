"""Deserialize a captured world snapshot back onto a live episode.

The gym can serialize its whole world (``GymState.to_json`` / ``WorldState.to_json``)
but had no way to load one back — so an episode could only be reset-to-seed and
fully replayed, never *resumed from a corrected mid-episode state*. This module
adds that missing half.

Design: the catalog (products / promotions / users / restaurants / coupons) is
deterministic from ``make_task(task_id, seed)``, and the shop snapshot doesn't
even serialize it — so we DON'T reconstruct the world from a snapshot. Instead
the caller resets to the seed baseline (rebuilding every catalog) and we OVERLAY
only the mutable slice an agent's actions change: cart, orders, returns,
subscriptions, the logged-in user + account edits, each sub-app's cart/orders/
mail/events, the cross-app event log, and the scheduler clock.

Reconstruction is reflection-based: for each mutable field we read the store's
own type hint and rebuild the (possibly nested) dataclasses from their ``asdict``
form, ignoring derived keys (``unread_count``, ``cart_count``, …) the snapshot
also carries. This keeps the codec correct as the model grows.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from typing import Any

from server.apps.bus import WorldEvent

# The mutable fields per store (everything else — catalog — comes from reset).
_MUTABLE_SHOP = ["cart", "orders", "returns", "subscriptions", "current_user_id", "step", "action_log", "flash_messages"]
_MUTABLE_SUBAPP = {
    "mail": ["account_email", "inbox", "sent", "drafts"],
    "food": ["cart", "orders"],
    "calendar": ["events"],
    "market": ["cart", "orders", "coupons"],
}


def _coerce(hint: Any, value: Any) -> Any:
    """Rebuild ``value`` (JSON) into the type named by ``hint`` (a resolved type
    annotation). Handles Optional/Union, list[X], dict[str, X], nested
    dataclasses, and primitives."""
    if value is None:
        return None
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if origin in (typing.Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        return _coerce(non_none[0], value) if len(non_none) == 1 else value
    if origin in (list, tuple):
        inner = args[0] if args else None
        seq = [_coerce(inner, v) for v in value]
        return tuple(seq) if origin is tuple else seq
    if origin is dict:
        vt = args[1] if len(args) == 2 else None
        return {k: _coerce(vt, v) for k, v in value.items()}
    if dataclasses.is_dataclass(hint) and isinstance(value, dict):
        return from_dict(hint, value)
    return value


def from_dict(cls: type, data: dict) -> Any:
    """Build a dataclass instance from its ``asdict`` form, ignoring keys that
    aren't real fields (derived values the snapshot also carries)."""
    if data is None:
        return None
    hints = typing.get_type_hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name in data:
            kwargs[f.name] = _coerce(hints.get(f.name, Any), data[f.name])
    return cls(**kwargs)


def _overlay(store: Any, snap: dict, field_names: list[str]) -> None:
    """Overlay the named mutable fields of ``store`` from a snapshot, rebuilding
    each into the field's declared type."""
    hints = typing.get_type_hints(type(store))
    for name in field_names:
        if name in snap:
            setattr(store, name, _coerce(hints.get(name, Any), snap[name]))


def _apply_account_edits(shop: Any, current_user_json: dict | None) -> None:
    """Overlay the logged-in user's editable account state (addresses, payment
    methods, 2FA, loyalty) — the shop snapshot carries the user under
    ``current_user`` even though it isn't a GymState field."""
    if not current_user_json:
        return
    uid = shop.current_user_id
    if not uid or uid not in shop.users:
        return
    user = shop.users[uid]
    hints = typing.get_type_hints(type(user))
    for name in ("addresses", "payment_methods", "two_fa_enabled", "loyalty_tier", "email", "full_name"):
        if name in current_user_json:
            setattr(user, name, _coerce(hints.get(name, Any), current_user_json[name]))


def apply_snapshot(world: Any, snap: dict) -> None:
    """Overlay a captured snapshot onto an already-reset (seed-baseline) world.

    ``snap`` may be a WorldState snapshot (has a ``shop`` key) or a bare GymState
    (shop) snapshot. Only the mutable slice is applied; catalogs stay at seed so
    delta / cross-app verifiers keep comparing against ``initial``/``initial_world``.
    """
    shop_json = snap.get("shop") if "shop" in snap else snap
    shop = world.shop
    _overlay(shop, shop_json, _MUTABLE_SHOP)
    _apply_account_edits(shop, shop_json.get("current_user"))

    for app, mutable in _MUTABLE_SUBAPP.items():
        store = getattr(world, app, None)
        app_json = snap.get(app)
        if store is not None and isinstance(app_json, dict):
            _overlay(store, app_json, mutable)

    if isinstance(snap.get("events"), list):
        world.events = [from_dict(WorldEvent, e) for e in snap["events"]]
    sched_json = snap.get("schedule")
    if isinstance(sched_json, dict):
        _overlay(world.schedule, sched_json, ["now", "queue"])
