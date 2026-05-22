"""Cross-app event log — the ONLY channel for cross-app effects.

Each app mutates ONLY its own store. When something in one app should
cause an effect in another (a shop order producing a confirmation email,
a food order producing a receipt + a calendar delivery slot), the
*producing* app calls :func:`emit`. That APPENDS a :class:`WorldEvent` to
``world.events`` (an append-only audit trail) and, if a subscriber is
registered for that event type, *delivers* it — the subscriber performs
the write on the TARGET app's store and the event is marked ``delivered``.

Why append-only + a ``delivered`` flag (this is load-bearing, not
decoration): from the outside, two very different situations look
identical —

  * the confirmation email was never produced   -> delivered = False  (ENV bug)
  * the email exists but the agent never read it -> delivered = True   (AGENT's fault)

Only the second is a real, sellable agent failure. The event log is the
ground truth that tells them apart. Without it we would harvest
environment bugs mislabeled as agent failure modes — exactly the noise
the whole project is trying to avoid. Verifiers assert the chain fired by
reading ``world.events``; the failure harvester reads it to know which
facts were *available* to the agent at each step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:                      # avoid a runtime import cycle world<->bus
    from server.apps.world import WorldState


# --------------------------------------------------------------------------- #
# The event
# --------------------------------------------------------------------------- #

@dataclass
class WorldEvent:
    """One cross-app effect. Immutable in spirit: once appended we only ever
    flip ``delivered`` to True; we never rewrite or drop a prior event."""

    id: str
    type: str                          # "ShopOrderPlaced" | "FoodOrderPlaced" | ...
    source_app: str                    # "shop"
    target_app: str                    # "mail"
    step: int
    payload: dict[str, Any] = field(default_factory=dict)
    delivered: bool = False


# --------------------------------------------------------------------------- #
# Subscriber registry
# --------------------------------------------------------------------------- #

# A subscriber receives (world, event) and performs the write on the TARGET
# app's store. Exactly ONE handler per event type keeps delivery
# deterministic and auditable (no fan-out ordering ambiguity).
Subscriber = Callable[["WorldState", "WorldEvent"], None]

_SUBSCRIBERS: dict[str, Subscriber] = {}


def subscribe(event_type: str, handler: Subscriber) -> None:
    """Register the handler that delivers ``event_type`` into its target
    store. Re-registering replaces the prior handler (last one wins)."""
    _SUBSCRIBERS[event_type] = handler


def clear_subscribers() -> None:
    """Test hook — wipe the registry so a test can install fakes in
    isolation. Production code registers its subscribers at import time."""
    _SUBSCRIBERS.clear()


def registered_types() -> set[str]:
    """The event types that currently have a delivery subscriber."""
    return set(_SUBSCRIBERS)


# --------------------------------------------------------------------------- #
# Emit + inspection
# --------------------------------------------------------------------------- #

def emit(
    world: "WorldState",
    *,
    type: str,
    source_app: str,
    target_app: str,
    payload: dict[str, Any] | None = None,
    step: int | None = None,
) -> WorldEvent:
    """Append a cross-app event to ``world.events`` and deliver it if a
    subscriber is registered for ``type``.

    Append-only: prior events are never mutated or removed. The returned
    event lets callers/tests inspect the result (incl. ``delivered``).
    """
    event = WorldEvent(
        id=f"evt_{len(world.events) + 1}",
        type=type,
        source_app=source_app,
        target_app=target_app,
        step=step if step is not None else world.step,
        payload=dict(payload or {}),
    )
    world.events.append(event)

    handler = _SUBSCRIBERS.get(type)
    if handler is not None:
        handler(world, event)
        event.delivered = True         # only true once the target store was written
    return event


def events_of_type(world: "WorldState", type: str) -> list[WorldEvent]:
    """All events of a given type, in emission order."""
    return [e for e in world.events if e.type == type]


def has_delivered(world: "WorldState", type: str) -> bool:
    """True iff at least one event of ``type`` was actually delivered.
    Verifiers use this to assert the cross-app chain genuinely fired."""
    return any(e.type == type and e.delivered for e in world.events)
