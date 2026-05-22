"""Pure-logic tests for the multi-app layer.

Commit 1 scope: the :class:`WorldState` wrapper + the append-only cross-app
event log (:mod:`server.apps.bus`). No browser, no FastAPI server — these
run under plain ``pytest`` with no Playwright dependency.

The behaviours pinned here are the ones the whole failure-harvesting story
leans on:
  * the existing ``GymState`` is wrapped, never copied or mutated;
  * the event log is append-only with stable, ordered ids;
  * an event with NO subscriber stays ``delivered=False`` (env never
    produced the effect) — distinguishable from a delivered event
    (``delivered=True``) that the agent simply never consumed.
"""

from __future__ import annotations

import pytest

from server.tasks import TASKS, make_task
from server.apps import bus
from server.apps.bus import emit, subscribe, clear_subscribers
from server.apps.world import WorldState

# Any valid shop task works — these tests only need a real GymState to wrap.
_TASK_ID = next(iter(TASKS))


@pytest.fixture(autouse=True)
def _clean_subscribers():
    # Each test starts and ends with an empty subscriber registry so tests
    # can install fakes without leaking into one another.
    clear_subscribers()
    yield
    clear_subscribers()


def _world(task_id: str = _TASK_ID, seed: int = 0) -> WorldState:
    return WorldState(shop=make_task(task_id, seed))


# --------------------------------------------------------------------------- #
# WorldState wraps GymState (unchanged)
# --------------------------------------------------------------------------- #

def test_worldstate_wraps_gymstate_unchanged():
    shop = make_task(_TASK_ID, 0)
    w = WorldState(shop=shop)
    assert w.shop is shop                       # same object, not a copy
    assert w.task_id == shop.task_id            # metadata delegates to shop
    assert w.seed == shop.seed
    assert w.step == shop.step
    assert w.finished == shop.finished
    assert w.mail is None and w.food is None and w.calendar is None
    assert w.events == []


def test_metadata_tracks_shop_mutations():
    w = _world()
    w.shop.step = 5
    w.shop.finished = True
    assert w.step == 5 and w.finished is True   # property, not a stale copy


# --------------------------------------------------------------------------- #
# Append-only event log
# --------------------------------------------------------------------------- #

def test_event_log_is_append_only_with_sequential_ids():
    w = _world()
    e1 = emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
              payload={"order_id": "SHOP-1"})
    e2 = emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
              payload={"order_id": "SHOP-2"})
    assert [e.id for e in w.events] == ["evt_1", "evt_2"]
    assert w.events[0] is e1 and w.events[1] is e2          # order preserved
    assert w.events[0].payload["order_id"] == "SHOP-1"      # earlier event untouched


def test_emit_copies_payload_so_caller_mutation_does_not_leak():
    w = _world()
    payload = {"order_id": "SHOP-1"}
    emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
         payload=payload)
    payload["order_id"] = "MUTATED"
    assert w.events[0].payload["order_id"] == "SHOP-1"


def test_emit_defaults_step_from_world():
    w = _world()
    w.shop.step = 7
    e = emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
             payload={})
    assert e.step == 7


# --------------------------------------------------------------------------- #
# Delivery: the env-bug vs agent-fault discriminator
# --------------------------------------------------------------------------- #

def test_event_without_subscriber_is_not_delivered():
    w = _world()
    e = emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
             payload={"order_id": "SHOP-1"})
    # No subscriber registered -> recorded but NOT delivered. This is the
    # signal that an env effect was never produced (NOT an agent failure).
    assert e.delivered is False
    assert w.events[0].delivered is False
    assert bus.has_delivered(w, "ShopOrderPlaced") is False


def test_subscriber_delivers_and_flips_delivered_flag():
    w = _world()
    seen: list[str] = []

    def handler(world, event):
        # A real subscriber writes the TARGET store; here we just record it.
        seen.append(event.payload["order_id"])

    subscribe("ShopOrderPlaced", handler)
    e = emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
             payload={"order_id": "SHOP-42"})
    assert e.delivered is True
    assert seen == ["SHOP-42"]
    assert bus.has_delivered(w, "ShopOrderPlaced") is True


def test_only_subscribed_type_is_delivered():
    w = _world()
    subscribe("ShopOrderPlaced", lambda world, event: None)
    emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail", payload={})
    emit(w, type="FoodOrderPlaced", source_app="food", target_app="mail", payload={})
    assert bus.has_delivered(w, "ShopOrderPlaced") is True
    assert bus.has_delivered(w, "FoodOrderPlaced") is False   # no handler -> not delivered


# --------------------------------------------------------------------------- #
# Inspection helpers
# --------------------------------------------------------------------------- #

def test_events_are_inspectable_by_type():
    w = _world()
    emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail", payload={})
    emit(w, type="FoodOrderPlaced", source_app="food", target_app="mail", payload={})
    emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail", payload={})
    assert len(bus.events_of_type(w, "ShopOrderPlaced")) == 2
    assert len(bus.events_of_type(w, "FoodOrderPlaced")) == 1
    assert {e.target_app for e in w.events} == {"mail"}


def test_worldstate_to_json_shape():
    w = _world()
    emit(w, type="ShopOrderPlaced", source_app="shop", target_app="mail",
         payload={"order_id": "X"})
    j = w.to_json()
    assert j["task_id"] == w.task_id
    assert isinstance(j["shop"], dict)
    assert j["mail"] is None and j["food"] is None and j["calendar"] is None
    assert j["events"][0]["type"] == "ShopOrderPlaced"
    assert j["events"][0]["delivered"] is False
