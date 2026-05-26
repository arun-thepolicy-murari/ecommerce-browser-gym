"""Cross-app (category M) verifier tests — pure-logic, no browser.

We drive the real shop / mail / food mutations + the cross-app event bus to
reproduce exactly what the server routes do, build a world-carrying Probe,
and assert the suite scores 1.0 on the full path and the right partial credit
otherwise. The verifier is the ground truth, so this is where its correctness
is pinned before any oracle / harvesting run.
"""

from __future__ import annotations

import copy

import pytest

from server import mutations
from server.state import log_action
from server.tasks import make_task
from server.verifiers import Probe, build_suite
from server.apps.world import WorldState
from server.apps import bus, scheduler, shop_hooks
from server.apps import wiring as apps_wiring
from server.apps.mail import mutations as mail_mut
from server.apps.food import mutations as food_mut
from server.apps.calendar import mutations as cal_mut


@pytest.fixture(autouse=True)
def _subscribers():
    # Register the real cross-app subscribers (as the server does at startup),
    # isolated per test.
    bus.clear_subscribers()
    apps_wiring.register_default_subscribers()
    yield
    bus.clear_subscribers()


class _CrossSim:
    """Drives a cross-app episode: shop + mail + food mutations, the event
    bus, and URL transitions, probing the world-aware verifier after each."""

    def __init__(self, task_id: str, seed: int = 0):
        built = make_task(task_id, seed)
        assert isinstance(built, WorldState), "M tasks must build a WorldState"
        self.world = built
        self.shop = self.world.shop
        self.initial = copy.deepcopy(self.shop)
        self.initial_world = copy.deepcopy(self.world)
        self.suite = build_suite(task_id)
        self.url = "/"
        self.step = 0

    def go(self, url: str) -> dict:
        self.url = url
        return self._probe()

    def do(self, fn) -> dict:
        fn()
        return self._probe()

    def _probe(self) -> dict:
        self.step += 1
        return self.suite.evaluate(
            Probe(state=self.shop, url=self.url, initial_state=self.initial,
                  world=self.world, initial_world=self.initial_world,
                  active_tab_url=self.url),
            self.step,
        )


# --------------------------------------------------------------------------- #
# M2 (north-star): order mouse -> open confirmation email -> use tracking link
# --------------------------------------------------------------------------- #

def _place_mouse_order(sim: _CrossSim, product_id: str = "p_mouse_wireless") -> str:
    mutations.add_to_cart(sim.shop, product_id, 1)
    mutations.place_order(sim.shop, "pay_visa")
    order_id = next(iter(sim.shop.orders))
    # The checkout route emits this after a successful place_order.
    shop_hooks.emit_shop_order_placed(sim.world, order_id)
    return order_id


def test_m2_full_path_scores_one():
    sim = _CrossSim("M2/order_then_track_via_email")
    sim.go("/product/p_mouse_wireless")
    oid = _place_mouse_order(sim)
    # Confirmation email was delivered by the subscriber.
    conf = next(e for e in sim.world.mail.inbox.values() if e.order_id == oid)
    # Agent opens it in Mail, then follows its tracking link (shop logs it).
    sim.go("/mail")
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, conf.id))
    sim.do(lambda: log_action(sim.shop, "viewed_tracking", order_id=oid))
    final = sim.go(conf.tracking_url)
    assert final["success"] is True
    assert final["score"] == 1.0


def test_m2_orders_but_never_checks_email_is_not_success():
    sim = _CrossSim("M2/order_then_track_via_email")
    res = None
    sim.go("/product/p_mouse_wireless")
    _place_mouse_order(sim)
    res = sim.go("/order/whatever")
    # Credit for ordering (0.30) + the chain firing (0.15), nothing more.
    assert res["success"] is False
    assert 0.40 <= res["score"] < 0.50
    assert "opened_confirmation_email" in res["missed_milestones"]
    assert "tracking_viewed_for_correct_order" in res["missed_milestones"]


def test_m2_tracking_wrong_order_id_does_not_credit():
    """Opening the email but viewing tracking for the WRONG order id (the
    order_id_memory_loss / wrong_source_of_truth failure) must NOT pass."""
    sim = _CrossSim("M2/order_then_track_via_email")
    oid = _place_mouse_order(sim)
    conf = next(e for e in sim.world.mail.inbox.values() if e.order_id == oid)
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, conf.id))
    # Agent fabricates a different order id for tracking.
    res = sim.do(lambda: log_action(sim.shop, "viewed_tracking",
                                    order_id="ORD-WRONG-0001"))
    assert res["success"] is False
    assert "tracking_viewed_for_correct_order" in res["missed_milestones"]
    assert "opened_confirmation_email" not in res["missed_milestones"]


def test_m2_wrong_mouse_fails_required_milestone():
    sim = _CrossSim("M2/order_then_track_via_email")
    sim.do(lambda: mutations.add_to_cart(sim.shop, "p_mouse_gaming", 1))
    res = sim.do(lambda: mutations.place_order(sim.shop, "pay_visa"))
    assert res["success"] is False
    assert "mouse_ordered" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M3: order dinner -> open the receipt email for that order
# --------------------------------------------------------------------------- #

def _place_food_order(sim: _CrossSim, restaurant_id="r_sushi",
                      dish_id="d_salmon_roll") -> str:
    food_mut.add_dish(sim.world.food, restaurant_id=restaurant_id,
                      dish_id=dish_id, quantity=1)
    food_mut.place_food_order(sim.world)        # emits FoodOrderPlaced
    return next(iter(sim.world.food.orders))


def test_m3_full_path_scores_one():
    sim = _CrossSim("M3/dinner_then_receipt")
    sim.go("/food")
    oid = _place_food_order(sim)
    receipt = next(e for e in sim.world.mail.inbox.values() if e.order_id == oid)
    sim.go("/mail")
    final = sim.do(lambda: mail_mut.mark_read(sim.world.mail, receipt.id))
    assert final["success"] is True
    assert final["score"] == 1.0


def test_m3_order_but_receipt_unopened_is_not_success():
    sim = _CrossSim("M3/dinner_then_receipt")
    _place_food_order(sim, restaurant_id="r_burger", dish_id="d_classic")
    res = sim.go("/mail")
    assert res["success"] is False
    # food_order_placed (0.40) + receipt_email_delivered (0.20) = 0.60
    assert 0.55 <= res["score"] < 0.65
    assert "opened_receipt_email" in res["missed_milestones"]


def test_m3_missing_subscriber_chain_not_credited():
    """If the food->mail subscriber is not wired (an ENVIRONMENT bug), the
    verifier must NOT credit the receipt milestones — the failure surfaces as
    an undelivered chain, not as the agent's fault."""
    sim = _CrossSim("M3/dinner_then_receipt")
    bus.clear_subscribers()                      # simulate the missing wiring
    _place_food_order(sim, restaurant_id="r_burger", dish_id="d_classic")
    res = sim.go("/mail")
    assert res["success"] is False
    assert "receipt_email_delivered" in res["missed_milestones"]
    assert "opened_receipt_email" in res["missed_milestones"]
    # The order itself still placed, so partial credit remains.
    assert "food_order_placed" not in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M15 (async): wait for the price-drop alert -> buy that mouse at the new price
# --------------------------------------------------------------------------- #

def _flush_pricedrop(sim: _CrossSim):
    """Advance the scheduler clock past the alert's fire step so the PAIR fires
    (PriceDropAlert -> Mail + ShopPriceChanged -> Shop), then return the alert
    email."""
    scheduler.advance_and_flush(sim.world, 4)
    return next(e for e in sim.world.mail.inbox.values()
                if "price-drop" in (e.labels or []))


def test_m15_paired_event_fires_and_drops_shop_price():
    """The injector's PAIR genuinely touches both apps: the email lands in Mail
    AND the shop price actually drops (so the new price is obtainable and a
    pre-drop buyer is provably stale)."""
    sim = _CrossSim("M15/inbox_price_watch")
    assert not bus.has_delivered(sim.world, "PriceDropAlert")  # not yet at step 0
    alert = _flush_pricedrop(sim)
    assert bus.has_delivered(sim.world, "PriceDropAlert")
    assert bus.has_delivered(sim.world, "ShopPriceChanged")
    assert alert.product_id == "p_mouse_ergonomic"
    assert sim.shop.products["p_mouse_ergonomic"].base_price == 34.99


def test_m15_full_path_scores_one():
    sim = _CrossSim("M15/inbox_price_watch")
    alert = _flush_pricedrop(sim)
    sim.go(f"/mail/message/{alert.id}")
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, alert.id))
    sim.do(lambda: mutations.add_to_cart(sim.shop, "p_mouse_ergonomic", 1))
    final = sim.do(lambda: mutations.place_order(sim.shop, "pay_visa"))
    assert final["success"] is True
    assert final["score"] == 1.0


def test_m15_outcome_without_opening_email_is_success():
    """The alert's SUBJECT line already names the mouse + new price, so buying
    the right mouse at the dropped price WITHOUT opening the email is full
    success — opening the email is informational, not required. (This is the
    Haiku case: it read the subject from the inbox list and ordered correctly.)"""
    sim = _CrossSim("M15/inbox_price_watch")
    _flush_pricedrop(sim)                       # alert delivered + price dropped; left UNREAD
    sim.do(lambda: mutations.add_to_cart(sim.shop, "p_mouse_ergonomic", 1))
    final = sim.do(lambda: mutations.place_order(sim.shop, "pay_visa"))
    assert final["success"] is True
    assert final["score"] == 1.0


def test_m15_wrong_mouse_fails_required_milestone():
    sim = _CrossSim("M15/inbox_price_watch")
    alert = _flush_pricedrop(sim)
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, alert.id))
    sim.do(lambda: mutations.add_to_cart(sim.shop, "p_mouse_mini", 1))
    res = sim.do(lambda: mutations.place_order(sim.shop, "pay_visa"))
    assert res["success"] is False
    assert "ordered_correct_mouse_only" in res["missed_milestones"]


def test_m15_buying_before_drop_is_stale_price():
    """An agent that buys the right mouse BEFORE the alert lands locks in the
    old $49.99 — the order line is provably stale and the new-price milestone
    must miss."""
    sim = _CrossSim("M15/inbox_price_watch")
    # Buy at step 0, before the price drop (base_price still 49.99).
    sim.do(lambda: mutations.add_to_cart(sim.shop, "p_mouse_ergonomic", 1))
    sim.do(lambda: mutations.place_order(sim.shop, "pay_visa"))
    placed = next(iter(sim.shop.orders.values()))
    assert placed.items[0].unit_price == 49.99
    # Now the alert lands and the agent reads it — too late, order is stale.
    alert = _flush_pricedrop(sim)
    res = sim.do(lambda: mail_mut.mark_read(sim.world.mail, alert.id))
    assert res["success"] is False
    assert "ordered_at_dropped_price" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M16 (hero async branch-flip + negative action): order dinner -> delay notice
# -> move the reminder to the new ETA (one event) + tell the guest
# --------------------------------------------------------------------------- #

def _order_dinner(sim: _CrossSim) -> None:
    food_mut.add_dish(sim.world.food, restaurant_id="r_sushi",
                      dish_id="d_salmon_roll", quantity=1)
    food_mut.place_food_order(sim.world)        # emits FoodOrderPlaced (step 0)


def _fire_delay(sim: _CrossSim):
    """Advance the clock past the delay's due step (FoodOrderPlaced.step + 5)
    so DeliveryDelayed fires, then return the delay-notice email."""
    scheduler.advance_and_flush(sim.world, 6)
    return next(e for e in sim.world.mail.inbox.values()
                if "delivery" in (e.labels or []))


def _tell_alex(sim: _CrossSim, body: str) -> None:
    mail_mut.send_email(sim.world.mail, to="alex@example.com",
                        subject="Dinner delivery", body=body)


def test_m16_delay_fires_only_after_food_order():
    """Relative trigger: no FoodOrderPlaced -> the delay never fires; once the
    order is placed it fires delay_steps later."""
    sim = _CrossSim("M16/coordinated_dinner_delay")
    scheduler.advance_and_flush(sim.world, 6)     # clock moves, but no trigger yet
    assert not bus.has_delivered(sim.world, "DeliveryDelayed")
    _order_dinner(sim)
    scheduler.advance_and_flush(sim.world, 12)
    assert bus.has_delivered(sim.world, "DeliveryDelayed")


def test_m16_full_path_scores_one():
    sim = _CrossSim("M16/coordinated_dinner_delay")
    _order_dinner(sim)
    # First plan at the original ETA (19:00).
    r = cal_mut.create_event(sim.world.calendar, title="Dinner delivery",
                             day="2026-05-22", start="19:00", end="19:30")
    notice = _fire_delay(sim)
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, notice.id))
    # Branch-flip: MOVE the same event to the new ETA (not a second one).
    cal_mut.update_event(sim.world.calendar, r["event_id"], start="20:00",
                         end="20:30")
    _tell_alex(sim, "Update — it'll now arrive around 8:00 PM.")
    final = sim._probe()
    assert final["success"] is True
    assert final["score"] == 1.0


def test_m16_over_keep_two_events_fails():
    """The negative action: leaving the old 19:00 reminder AND adding a new
    20:00 one -> two user events -> the calendar milestone misses."""
    sim = _CrossSim("M16/coordinated_dinner_delay")
    _order_dinner(sim)
    cal_mut.create_event(sim.world.calendar, title="Dinner delivery",
                         day="2026-05-22", start="19:00", end="19:30")
    notice = _fire_delay(sim)
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, notice.id))
    cal_mut.create_event(sim.world.calendar, title="Dinner delivery (new)",
                         day="2026-05-22", start="20:00", end="20:30")
    _tell_alex(sim, "Update — it'll now arrive around 8:00 PM.")
    res = sim._probe()
    assert res["success"] is False
    assert "calendar_reflects_new_eta_only" in res["missed_milestones"]


def test_m16_reminder_never_moved_fails():
    """Reading the delay but leaving the reminder at the stale 19:00 -> miss."""
    sim = _CrossSim("M16/coordinated_dinner_delay")
    _order_dinner(sim)
    cal_mut.create_event(sim.world.calendar, title="Dinner delivery",
                         day="2026-05-22", start="19:00", end="19:30")
    notice = _fire_delay(sim)
    sim.do(lambda: mail_mut.mark_read(sim.world.mail, notice.id))
    _tell_alex(sim, "Update — it'll now arrive around 8:00 PM.")
    res = sim._probe()
    assert res["success"] is False
    assert "calendar_reflects_new_eta_only" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# Backward-compat: probe.state still aliases the shop GymState
# --------------------------------------------------------------------------- #

def test_probe_state_aliases_world_shop():
    sim = _CrossSim("M2/order_then_track_via_email")
    assert sim.world.shop is sim.shop
