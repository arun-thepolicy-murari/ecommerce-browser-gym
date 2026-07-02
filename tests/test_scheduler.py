"""Pure-logic tests for the deterministic async event injector.

These lock the property the whole multi-tab-async benchmark rests on: events
fire on a DETERMINISTIC step clock (never wall-clock), reusing the bus so the
audit trail + delivered-flag semantics carry over. No browser, no server.
"""

from __future__ import annotations

import pytest

from server.tasks import TASKS, make_task
from server.apps import bus
from server.apps.bus import subscribe, clear_subscribers
from server.apps.world import WorldState
from server.apps import scheduler
from server.apps.scheduler import (
    advance_and_flush, schedule_absolute, schedule_relative,
)

# _mark_subscriber writes to world.shop.flash_messages, and _world() wraps the
# factory result as a WorldState. Category-M factories now return a WorldState
# (multi-app) which has no flash_messages and a read-only `step`; wrapping one
# would double-nest. Pin a single-app task whose factory yields a plain GymState.
_TASK_ID = "A1/buy_wireless_mouse"


def _world() -> WorldState:
    # A fresh WorldState (its default ScheduleState queue is empty).
    return WorldState(shop=make_task(_TASK_ID, 0))


@pytest.fixture(autouse=True)
def _clean_subscribers():
    clear_subscribers()
    yield
    clear_subscribers()


def _mark_subscriber(world, event):
    # Fake delivery: stash a marker on the shop store so we can assert delivery.
    world.shop.flash_messages.append(("sched", event.type))


def test_absolute_fires_exactly_at_step():
    w = _world()
    subscribe("PriceDropAlert", _mark_subscriber)
    schedule_absolute(w.schedule, id="se1", fire_at_step=3,
                      emit_type="PriceDropAlert", source_app="shop",
                      target_app="mail", payload={"p": 1})

    assert advance_and_flush(w, 2) == []          # before due -> nothing
    assert len(w.events) == 0
    fired = advance_and_flush(w, 3)               # at due -> fires
    assert [e.type for e in fired] == ["PriceDropAlert"]
    assert bus.has_delivered(w, "PriceDropAlert")  # subscriber ran
    assert w.schedule.queue[0].fired and w.schedule.queue[0].fired_at_step == 3


def test_relative_not_due_without_trigger():
    w = _world()
    schedule_relative(w.schedule, id="se_refund", after_event_type="ReturnFiled",
                      delay_steps=3, emit_type="RefundApproved",
                      source_app="shop", target_app="mail")
    # No trigger event ever -> never due, even far in the future.
    assert advance_and_flush(w, 50) == []
    assert not any(e.type == "RefundApproved" for e in w.events)


def test_relative_fires_delay_after_trigger():
    # The clock advances monotonically by 1, as the real harness drives it.
    w = _world()
    schedule_relative(w.schedule, id="se_refund", after_event_type="ReturnFiled",
                      delay_steps=3, emit_type="RefundApproved",
                      source_app="shop", target_app="mail")
    advance_and_flush(w, 1)
    advance_and_flush(w, 2)                        # no trigger yet -> nothing
    assert not any(e.type == "RefundApproved" for e in w.events)
    # Agent files the return at step 3 (a trigger event lands in the log).
    bus.emit(w, type="ReturnFiled", source_app="shop", target_app="shop",
             step=3, payload={"order_id": "ORD-1"})
    assert advance_and_flush(w, 5) == []          # 3+3=6 not reached
    fired = advance_and_flush(w, 6)               # due at 6
    assert [e.type for e in fired] == ["RefundApproved"]


def test_clock_is_monotonic_and_idempotent():
    w = _world()
    schedule_absolute(w.schedule, id="se1", fire_at_step=2,
                      emit_type="X", source_app="a", target_app="b")
    advance_and_flush(w, 5)                        # fires once (5 >= 2)
    n_after_first = len(w.events)
    assert n_after_first == 1
    assert advance_and_flush(w, 5) == []           # same step -> no-op
    assert advance_and_flush(w, 4) == []           # backwards -> no-op
    assert len(w.events) == n_after_first          # never re-emits


def test_fired_is_append_only_no_reemit():
    w = _world()
    schedule_absolute(w.schedule, id="se1", fire_at_step=1,
                      emit_type="X", source_app="a", target_app="b")
    advance_and_flush(w, 1)
    advance_and_flush(w, 2)
    advance_and_flush(w, 3)
    assert sum(1 for e in w.events if e.type == "X") == 1   # exactly once


def test_no_subscriber_emits_but_not_delivered():
    # Mirrors the bus contract: a scheduled event with NO subscriber is still
    # appended (env truth) but delivered=False — env-bug vs agent-miss stays
    # distinguishable.
    w = _world()
    schedule_absolute(w.schedule, id="se1", fire_at_step=1,
                      emit_type="NoHandler", source_app="a", target_app="b")
    advance_and_flush(w, 1)
    assert any(e.type == "NoHandler" for e in w.events)
    assert not bus.has_delivered(w, "NoHandler")


def test_determinism_identical_sequences_match():
    def run():
        w = _world()
        schedule_absolute(w.schedule, id="b_price", fire_at_step=4,
                          emit_type="PriceDropAlert", source_app="shop",
                          target_app="mail")
        schedule_relative(w.schedule, id="a_refund",
                          after_event_type="ReturnFiled", delay_steps=2,
                          emit_type="RefundApproved", source_app="shop",
                          target_app="mail")
        out = []
        for step in range(1, 8):
            if step == 3:
                bus.emit(w, type="ReturnFiled", source_app="shop",
                         target_app="shop", step=3)
            out += [(e.type, e.step) for e in advance_and_flush(w, step)]
        return out
    assert run() == run()   # same (task, seed, sequence) -> identical firings


def test_schedule_json_shape():
    w = _world()
    schedule_absolute(w.schedule, id="se1", fire_at_step=2,
                      emit_type="X", source_app="a", target_app="b")
    j = w.schedule.to_json()
    assert set(j) == {"now", "queue", "pending"}
    assert j["pending"] == 1 and j["now"] == 0
    advance_and_flush(w, 2)
    assert w.schedule.to_json()["pending"] == 0
