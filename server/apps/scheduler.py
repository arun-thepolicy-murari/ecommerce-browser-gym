"""Deterministic async event injector — the scheduled-event queue + clock.

Single-tab benchmarks can't test async handling: a new email / price drop /
notification arriving WHILE the agent is mid-task on another tab. This module
adds a DETERMINISTIC, step-driven scheduler on top of the existing event bus.

Events are scheduled at seed time (per task) to fire either:
  * ABSOLUTE  — when the clock reaches ``fire_at_step`` (e.g. a price-drop email
    lands at step 4), or
  * RELATIVE  — ``delay_steps`` after the FIRST :class:`WorldEvent` of
    ``after_event_type`` appears in ``world.events`` (e.g. a refund email arrives
    3 steps after the agent files a return — independent of what it does between).

At each step boundary the harness ticks the clock; every due event is delivered
through the EXISTING :func:`server.apps.bus.emit`, so the same subscribers and
the same append-only audit trail are reused — nothing here writes an app store
directly.

Determinism (load-bearing — the whole project rests on byte-reproducible
resets): the clock IS the harness step counter, advanced monotonically. No
wall-clock, no ``datetime.now()``, no background thread. The same (task, seed)
replays identically. Multi-app effects use a PAIR of scheduled events at the
same step (one per target app), since the bus is one-event-one-target.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from server.apps import bus

if TYPE_CHECKING:
    from server.apps.world import WorldState
    from server.apps.bus import WorldEvent


@dataclass
class ScheduledEvent:
    """One future cross-app effect. Append-only in spirit: ``fired`` only ever
    flips False -> True; we never rewrite or drop a scheduled entry."""

    id: str
    emit_type: str                       # the WorldEvent type to emit (bus reuses subscribers)
    source_app: str
    target_app: str
    payload: dict[str, Any] = field(default_factory=dict)
    # exactly one trigger kind is set:
    fire_at_step: int | None = None      # absolute
    after_event_type: str | None = None  # relative trigger event type
    delay_steps: int = 0                 # relative: fire this many steps after the trigger
    # state:
    fired: bool = False
    fired_at_step: int = -1


@dataclass
class ScheduleState:
    queue: list[ScheduledEvent] = field(default_factory=list)
    now: int = 0                         # simulated clock = highest step seen

    def to_json(self) -> dict[str, Any]:
        return {
            "now": self.now,
            "queue": [asdict(s) for s in self.queue],
            "pending": sum(1 for s in self.queue if not s.fired),
        }


# --------------------------------------------------------------------------- #
# Seeding helpers (used by task factories)
# --------------------------------------------------------------------------- #

def schedule_absolute(sched: ScheduleState, *, id: str, fire_at_step: int,
                      emit_type: str, source_app: str, target_app: str,
                      payload: dict[str, Any] | None = None) -> ScheduledEvent:
    se = ScheduledEvent(
        id=id, emit_type=emit_type, source_app=source_app,
        target_app=target_app, payload=dict(payload or {}),
        fire_at_step=fire_at_step)
    sched.queue.append(se)
    return se


def schedule_relative(sched: ScheduleState, *, id: str, after_event_type: str,
                      delay_steps: int, emit_type: str, source_app: str,
                      target_app: str,
                      payload: dict[str, Any] | None = None) -> ScheduledEvent:
    se = ScheduledEvent(
        id=id, emit_type=emit_type, source_app=source_app,
        target_app=target_app, payload=dict(payload or {}),
        after_event_type=after_event_type, delay_steps=delay_steps)
    sched.queue.append(se)
    return se


# --------------------------------------------------------------------------- #
# The clock
# --------------------------------------------------------------------------- #

def _resolve_due_step(world: "WorldState", se: ScheduledEvent) -> int | None:
    """The step at which ``se`` becomes due, or None if its trigger hasn't
    happened yet. Absolute -> fire_at_step. Relative -> first matching world
    event's step + delay_steps (None until that trigger event has fired)."""
    if se.fire_at_step is not None:
        return se.fire_at_step
    if se.after_event_type is not None:
        matches = bus.events_of_type(world, se.after_event_type)
        if matches:
            return matches[0].step + se.delay_steps
        return None
    return None


def advance_and_flush(world: "WorldState", step: int) -> list["WorldEvent"]:
    """Advance the clock to ``step`` and deliver every scheduled event now due.

    Monotonic + idempotent: ``step <= now`` is a no-op (protects against the
    same step being ticked twice). Deterministic: the queue is iterated in
    stable id order and each due event is delivered via ``bus.emit``. Returns
    the WorldEvents fired this tick (empty if none / no schedule)."""
    sched = getattr(world, "schedule", None)
    if sched is None or step <= sched.now:
        return []
    sched.now = step
    fired: list["WorldEvent"] = []
    for se in sorted(sched.queue, key=lambda s: s.id):
        if se.fired:
            continue
        due = _resolve_due_step(world, se)
        if due is not None and step >= due:
            evt = bus.emit(
                world, type=se.emit_type, source_app=se.source_app,
                target_app=se.target_app, payload=dict(se.payload), step=step)
            se.fired = True
            se.fired_at_step = step
            fired.append(evt)
    return fired
