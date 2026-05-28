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
from server.apps.market import mutations as market_mut


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
# M17 (cross-retailer): compare both stores + the emailed coupon, buy cheaper
# --------------------------------------------------------------------------- #

def _buy_monitor_valuemart(sim: _CrossSim, coupon: str | None = None) -> None:
    market_mut.add_to_cart(sim.world.market, product_id="vm_monitor_24")
    if coupon:
        market_mut.apply_coupon(sim.world.market, coupon)
    market_mut.place_order(sim.world)


def test_m17_full_path_buys_cheaper_store_with_coupon():
    sim = _CrossSim("M17/cross_retailer_cheaper")
    _buy_monitor_valuemart(sim, coupon="VALUE10")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m17_buying_on_shopgym_is_wrong_store():
    """Sticker says ShopGym ($199.99 < $209.99); buying there is the trap."""
    sim = _CrossSim("M17/cross_retailer_cheaper")
    mutations.add_to_cart(sim.shop, "p_monitor_24", 1)
    mutations.place_order(sim.shop, "pay_visa")
    res = sim._probe()
    assert res["success"] is False
    assert "ordered_monitor_on_valuemart" in res["missed_milestones"]


def test_m17_valuemart_without_coupon_fails():
    """Right store but no coupon -> ValueMart ($209.99) isn't actually cheaper
    than ShopGym's deal ($205.98), so the coupon milestone must miss."""
    sim = _CrossSim("M17/cross_retailer_cheaper")
    _buy_monitor_valuemart(sim, coupon=None)
    res = sim._probe()
    assert res["success"] is False
    assert "applied_value10_coupon" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M18 (async coupon-flip): commit to ShopGym -> flip email -> switch to ValueMart
# --------------------------------------------------------------------------- #

def _buy_gear_valuemart(sim: _CrossSim, coupon: str | None = None) -> None:
    market_mut.add_to_cart(sim.world.market, product_id="vm_laptop_studio")
    market_mut.add_to_cart(sim.world.market, product_id="vm_kb_mech")
    if coupon:
        market_mut.apply_coupon(sim.world.market, coupon)
    market_mut.place_order(sim.world)


def test_m18_flip_fires_via_absolute_fallback():
    sim = _CrossSim("M18/async_coupon_flip")
    assert not bus.has_delivered(sim.world, "CouponFlipAlert")
    scheduler.advance_and_flush(sim.world, 8)        # step-8 fallback
    assert bus.has_delivered(sim.world, "CouponFlipAlert")
    flips = [e for e in sim.world.mail.inbox.values()
             if "coupon-flip" in (e.labels or [])]
    assert len(flips) == 1


def test_m18_flip_email_deduped_when_both_triggers_fire():
    """Dynamic (on-checkout) + absolute fallback both emit CouponFlipAlert, but
    idempotent delivery yields exactly ONE flip email."""
    sim = _CrossSim("M18/async_coupon_flip")
    shop_hooks.emit_shop_checkout_reached(sim.world)  # arms the relative trigger
    scheduler.advance_and_flush(sim.world, 9)         # fires relative (due 1) + absolute (due 8)
    flips = [e for e in sim.world.mail.inbox.values()
             if "coupon-flip" in (e.labels or [])]
    assert len(flips) == 1


def test_m18_full_path_switches_to_valuemart():
    sim = _CrossSim("M18/async_coupon_flip")
    scheduler.advance_and_flush(sim.world, 8)         # flip lands
    _buy_gear_valuemart(sim, coupon="VALUEMART30")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m18_sunk_cost_buying_shopgym_fails():
    """Barrel through the ShopGym order (the sunk-cost failure) -> the ValueMart
    milestone never fires."""
    sim = _CrossSim("M18/async_coupon_flip")
    mutations.add_to_cart(sim.shop, "p_laptop_studio", 1)
    mutations.add_to_cart(sim.shop, "p_kb_mech", 1)
    mutations.place_order(sim.shop, "pay_visa")
    res = sim._probe()
    assert res["success"] is False
    assert "ordered_gear_on_valuemart" in res["missed_milestones"]


def test_m18_valuemart_without_flip_coupon_fails():
    """Switched stores but used the OLD VALUE10 instead of the flip's
    VALUEMART30 -> the flip-coupon milestone misses."""
    sim = _CrossSim("M18/async_coupon_flip")
    scheduler.advance_and_flush(sim.world, 8)
    _buy_gear_valuemart(sim, coupon="VALUE10")
    res = sim._probe()
    assert res["success"] is False
    assert "applied_valuemart30" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M19 (coupon minefield): reject the expired 50%, use the valid 10%, under budget
# --------------------------------------------------------------------------- #

def _buy_kbmouse_valuemart(sim: _CrossSim, coupon: str | None = None) -> None:
    market_mut.add_to_cart(sim.world.market, product_id="vm_kb_mech")
    market_mut.add_to_cart(sim.world.market, product_id="vm_mouse_wireless")
    if coupon:
        market_mut.apply_coupon(sim.world.market, coupon)
    market_mut.place_order(sim.world)


def test_m19_full_path_valid_coupon_under_budget():
    sim = _CrossSim("M19/coupon_minefield")
    _buy_kbmouse_valuemart(sim, coupon="VALUE10")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m19_expired_coupon_is_rejected():
    """The salient 50% code is expired -> the store rejects it and applies
    nothing (so the agent must fall back to the valid code)."""
    sim = _CrossSim("M19/coupon_minefield")
    market_mut.add_to_cart(sim.world.market, product_id="vm_kb_mech")
    r = market_mut.apply_coupon(sim.world.market, "VALUEMART50")
    assert r["ok"] is False and r["error"] == "expired"
    assert sim.world.market.cart.applied_coupon is None


def test_m19_no_coupon_busts_budget_fails():
    """The coupon is load-bearing: ValueMart keyboard+mouse without it is
    $134.98 > $125 -> both the budget and coupon milestones miss."""
    sim = _CrossSim("M19/coupon_minefield")
    _buy_kbmouse_valuemart(sim, coupon=None)
    res = sim._probe()
    assert res["success"] is False
    assert "under_budget" in res["missed_milestones"]
    assert "applied_value10" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M20 (bundled errand run): all sub-goals required; dropping one fails
# --------------------------------------------------------------------------- #

def _m20_gear(sim: _CrossSim) -> float:
    market_mut.add_to_cart(sim.world.market, product_id="vm_kb_mech")
    market_mut.add_to_cart(sim.world.market, product_id="vm_mouse_wireless")
    market_mut.apply_coupon(sim.world.market, "VALUE10")
    market_mut.place_order(sim.world)
    return next(o.total for o in sim.world.market.orders.values()
                if o.coupon_code == "VALUE10")


def _m20_dinner(sim: _CrossSim) -> None:
    food_mut.add_dish(sim.world.food, restaurant_id="r_sushi",
                      dish_id="d_salmon_roll")
    food_mut.place_food_order(sim.world)


def _m20_calendar(sim: _CrossSim) -> None:
    cal_mut.create_event(sim.world.calendar, title="Sushi delivery",
                         day="2026-05-22", start="19:00", end="19:30")


def _m20_reply(sim: _CrossSim, total: float) -> None:
    mail_mut.send_email(sim.world.mail, to="alex@example.com",
                        subject="Re: cost", body=f"It came to ${total:.2f} total.")


def test_m20_full_path_all_subgoals():
    sim = _CrossSim("M20/errand_run")
    total = _m20_gear(sim)
    _m20_dinner(sim)
    _m20_calendar(sim)
    _m20_reply(sim, total)
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m20_dropped_calendar_reminder_fails():
    sim = _CrossSim("M20/errand_run")
    total = _m20_gear(sim)
    _m20_dinner(sim)
    _m20_reply(sim, total)            # everything BUT the calendar reminder
    res = sim._probe()
    assert res["success"] is False
    assert "calendar_reminder_created" in res["missed_milestones"]


def test_m20_dropped_reply_fails():
    sim = _CrossSim("M20/errand_run")
    _m20_gear(sim)
    _m20_dinner(sim)
    _m20_calendar(sim)               # everything BUT the reply to Alex
    res = sim._probe()
    assert res["success"] is False
    assert "replied_gear_total_to_alex" in res["missed_milestones"]


def test_m20_wrong_total_in_reply_fails():
    """Reporting a paraphrased / wrong total (not the exact charge) misses."""
    sim = _CrossSim("M20/errand_run")
    _m20_gear(sim)
    _m20_dinner(sim)
    _m20_calendar(sim)
    mail_mut.send_email(sim.world.mail, to="alex@example.com",
                        subject="Re", body="It was about $130.")  # wrong number
    res = sim._probe()
    assert res["success"] is False
    assert "replied_gear_total_to_alex" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M21 (async errand run): juggle × async flip -> exact total is a MOVING TARGET
# --------------------------------------------------------------------------- #

def _m21_gear_postflip(sim: _CrossSim) -> float:
    """Buy keyboard+mouse on ValueMart with the POST-FLIP coupon VALUEMART20."""
    market_mut.add_to_cart(sim.world.market, product_id="vm_kb_mech")
    market_mut.add_to_cart(sim.world.market, product_id="vm_mouse_wireless")
    market_mut.apply_coupon(sim.world.market, "VALUEMART20")
    market_mut.place_order(sim.world)
    return next(o.total for o in sim.world.market.orders.values()
               if o.coupon_code == "VALUEMART20")


def test_m21_flip_fires_at_step_4():
    sim = _CrossSim("M21/async_errand_run")
    assert not bus.has_delivered(sim.world, "CouponFlipAlert")
    scheduler.advance_and_flush(sim.world, 4)            # absolute step-4 arrival
    assert bus.has_delivered(sim.world, "CouponFlipAlert")
    flips = [e for e in sim.world.mail.inbox.values()
             if "coupon-flip" in (e.labels or [])]
    assert len(flips) == 1 and "VALUEMART20" in flips[0].body


def test_m21_full_path_postflip_total():
    sim = _CrossSim("M21/async_errand_run")
    scheduler.advance_and_flush(sim.world, 4)            # flip lands
    total = _m21_gear_postflip(sim)
    assert round(total, 2) == 107.98                     # post-flip, not 121.48
    _m20_dinner(sim)
    _m20_calendar(sim)
    _m20_reply(sim, total)                               # reply carries 107.98
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m21_stale_total_reply_fails():
    """Applied the flip coupon (paid $107.98) but reported the STALE $121.48 to
    Alex -> the value went out of date under load; the reply milestone misses."""
    sim = _CrossSim("M21/async_errand_run")
    scheduler.advance_and_flush(sim.world, 4)
    _m21_gear_postflip(sim)                              # actually paid 107.98
    _m20_dinner(sim)
    _m20_calendar(sim)
    mail_mut.send_email(sim.world.mail, to="alex@example.com",
                        subject="Re: cost",
                        body="It came to $121.48 total.")  # the pre-flip number
    res = sim._probe()
    assert res["success"] is False
    assert "replied_postflip_total_to_alex" in res["missed_milestones"]


def test_m21_missed_flip_uses_value10_fails():
    """Bought gear with the stale VALUE10 (never caught the flip) -> the
    flip-coupon milestone misses."""
    sim = _CrossSim("M21/async_errand_run")
    scheduler.advance_and_flush(sim.world, 4)
    market_mut.add_to_cart(sim.world.market, product_id="vm_kb_mech")
    market_mut.add_to_cart(sim.world.market, product_id="vm_mouse_wireless")
    market_mut.apply_coupon(sim.world.market, "VALUE10")
    market_mut.place_order(sim.world)
    _m20_dinner(sim)
    _m20_calendar(sim)
    res = sim._probe()
    assert res["success"] is False
    assert "ordered_gear_with_flip_coupon" in res["missed_milestones"]


def test_m21_dropped_subgoal_under_load_fails():
    """Did gear (post-flip) + dinner + reply but dropped the calendar reminder
    (the M20 juggling failure persists even with the flip handled)."""
    sim = _CrossSim("M21/async_errand_run")
    scheduler.advance_and_flush(sim.world, 4)
    total = _m21_gear_postflip(sim)
    _m20_dinner(sim)
    _m20_reply(sim, total)                               # no calendar reminder
    res = sim._probe()
    assert res["success"] is False
    assert "calendar_reminder_created" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M22 (async calendar cascade): destructive overwrite + ripple under load
# --------------------------------------------------------------------------- #

def _m22_ids(sim: _CrossSim):
    evs = sim.world.calendar.events
    sync = next(e for e in evs.values() if "team sync" in e.title.lower())
    one = next(e for e in evs.values() if "priya" in e.title.lower())
    return sync.id, one.id


def _m22_coffee(sim: _CrossSim) -> None:
    food_mut.add_dish(sim.world.food, restaurant_id="r_bean", dish_id="d_latte")
    food_mut.place_food_order(sim.world)


def _m22_move_and_delete(sim: _CrossSim) -> None:
    sync_id, one_id = _m22_ids(sim)
    cal_mut.update_event(sim.world.calendar, one_id, start="14:00", end="15:00")
    cal_mut.delete_event(sim.world.calendar, sync_id)


def _m22_notify(sim: _CrossSim) -> None:
    mail_mut.send_email(sim.world.mail, to="priya@example.com",
                        subject="Re: Our 1:1 today",
                        body="Moved our 1:1 up to 2:00 PM today — see you then!")


def test_m22_change_alert_fires_at_step_4():
    sim = _CrossSim("M22/async_calendar_cascade")
    assert not bus.has_delivered(sim.world, "CalendarChangeAlert")
    scheduler.advance_and_flush(sim.world, 4)
    assert bus.has_delivered(sim.world, "CalendarChangeAlert")
    alerts = [e for e in sim.world.mail.inbox.values()
              if "calendar-change" in (e.labels or [])]
    assert len(alerts) == 1


def test_m22_full_path_all_subgoals():
    sim = _CrossSim("M22/async_calendar_cascade")
    scheduler.advance_and_flush(sim.world, 4)
    _m22_coffee(sim)
    _m22_move_and_delete(sim)
    _m22_notify(sim)
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m22_kept_stale_sync_double_books_fails():
    """THE destructive trap: moved the 1:1 to 2 PM but forgot to DELETE the
    cancelled Team Sync -> 2 PM is double-booked, so the deletion milestone
    misses."""
    sim = _CrossSim("M22/async_calendar_cascade")
    scheduler.advance_and_flush(sim.world, 4)
    _m22_coffee(sim)
    sync_id, one_id = _m22_ids(sim)
    cal_mut.update_event(sim.world.calendar, one_id, start="14:00", end="15:00")
    _m22_notify(sim)                      # everything BUT deleting the sync
    res = sim._probe()
    assert res["success"] is False
    assert "cancelled_sync_deleted" in res["missed_milestones"]


def test_m22_forgot_notify_priya_fails():
    sim = _CrossSim("M22/async_calendar_cascade")
    scheduler.advance_and_flush(sim.world, 4)
    _m22_coffee(sim)
    _m22_move_and_delete(sim)             # calendar fixed, but Priya not told
    res = sim._probe()
    assert res["success"] is False
    assert "notified_priya_new_time" in res["missed_milestones"]


def test_m22_dropped_coffee_under_load_fails():
    sim = _CrossSim("M22/async_calendar_cascade")
    scheduler.advance_and_flush(sim.world, 4)
    _m22_move_and_delete(sim)
    _m22_notify(sim)                      # handled the change but dropped the coffee
    res = sim._probe()
    assert res["success"] is False
    assert "coffee_ordered" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M23 (offsite that keeps moving): derive + conflict + cascade + recipient
# --------------------------------------------------------------------------- #

def _m23_lunch(sim: _CrossSim, *, veggie: bool, classic_qty: int = 1,
              fries_qty: int = 0) -> None:
    if veggie:
        food_mut.add_dish(sim.world.food, restaurant_id="r_burger",
                          dish_id="d_veggie")
    if classic_qty:
        food_mut.add_dish(sim.world.food, restaurant_id="r_burger",
                          dish_id="d_classic", quantity=classic_qty)
    if fries_qty:
        food_mut.add_dish(sim.world.food, restaurant_id="r_burger",
                          dish_id="d_fries", quantity=fries_qty)
    food_mut.place_food_order(sim.world)


def _m23_book(sim: _CrossSim, start: str) -> None:
    cal_mut.create_event(sim.world.calendar, title="Team Offsite Lunch",
                         day="2026-05-22", start=start, end="17:00")


def _m23_notify(sim: _CrossSim, who: str) -> None:
    mail_mut.send_email(sim.world.mail, to=who, subject="Team lunch — confirmed",
                        body="Confirmed: team lunch at 4:00 PM today.")


def test_m23_swap_fires_at_step_5():
    sim = _CrossSim("M23/offsite_keeps_moving")
    assert not bus.has_delivered(sim.world, "OffsiteChangeAlert")
    scheduler.advance_and_flush(sim.world, 5)
    assert bus.has_delivered(sim.world, "OffsiteChangeAlert")
    alerts = [e for e in sim.world.mail.inbox.values()
              if "offsite-change" in (e.labels or [])]
    assert len(alerts) == 1 and "dana@example.com" in alerts[0].body


def test_m23_full_path_all_blockers():
    sim = _CrossSim("M23/offsite_keeps_moving")
    scheduler.advance_and_flush(sim.world, 5)
    _m23_lunch(sim, veggie=True, classic_qty=1)        # has veggie, ~$22 < $40
    _m23_book(sim, "16:00")                            # after 3 PM, free
    for who in ("dana@example.com", "priya@example.com", "alex@example.com"):
        _m23_notify(sim, who)
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m23_forgot_veggie_fails():
    """Ordered only cheeseburgers — ignored Priya's vegetarian need."""
    sim = _CrossSim("M23/offsite_keeps_moving")
    scheduler.advance_and_flush(sim.world, 5)
    _m23_lunch(sim, veggie=False, classic_qty=2)
    _m23_book(sim, "16:00")
    for who in ("dana@example.com", "priya@example.com", "alex@example.com"):
        _m23_notify(sim, who)
    res = sim._probe()
    assert res["success"] is False
    assert "lunch_veg_under_budget" in res["missed_milestones"]


def test_m23_busted_budget_fails():
    """Has the veggie burger but blew past Alex's $40 cap."""
    sim = _CrossSim("M23/offsite_keeps_moving")
    scheduler.advance_and_flush(sim.world, 5)
    _m23_lunch(sim, veggie=True, classic_qty=4, fries_qty=2)   # ~$57 > $40
    _m23_book(sim, "16:00")
    for who in ("dana@example.com", "priya@example.com", "alex@example.com"):
        _m23_notify(sim, who)
    res = sim._probe()
    assert res["success"] is False
    assert "lunch_veg_under_budget" in res["missed_milestones"]


def test_m23_booked_before_3pm_fails():
    """Booked at 1 PM (valid pre-cascade) but never moved it after Dana's
    after-3 PM constraint landed."""
    sim = _CrossSim("M23/offsite_keeps_moving")
    scheduler.advance_and_flush(sim.world, 5)
    _m23_lunch(sim, veggie=True, classic_qty=1)
    _m23_book(sim, "13:00")                            # after 1 PM, NOT after 3 PM
    for who in ("dana@example.com", "priya@example.com", "alex@example.com"):
        _m23_notify(sim, who)
    res = sim._probe()
    assert res["success"] is False
    assert "meeting_after_3pm_free" in res["missed_milestones"]


def test_m23_notified_manager_not_dana_fails():
    """The recipient trap: confirmed to the old crew + the manager, but never
    told Dana directly (replied to the manager's email instead of composing)."""
    sim = _CrossSim("M23/offsite_keeps_moving")
    scheduler.advance_and_flush(sim.world, 5)
    _m23_lunch(sim, veggie=True, classic_qty=1)
    _m23_book(sim, "16:00")
    _m23_notify(sim, "priya@example.com")
    _m23_notify(sim, "alex@example.com")
    _m23_notify(sim, "manager@example.com")            # wrong target, not Dana
    res = sim._probe()
    assert res["success"] is False
    assert "notified_dana" in res["missed_milestones"]


def test_m23_wrong_slot_and_wrong_time_fails():
    """Verifier-fix regression: booking a DIFFERENT after-3 PM slot (19:00 — the
    form default, now a busy slot) and telling everyone '7 PM' consistently must
    miss BOTH the calendar milestone (only 16:00 is the unique valid slot) and
    the notify milestones (the stated time isn't the required 4 PM). Guards
    against the earlier ambiguity that wrongly credited an alternate slot."""
    sim = _CrossSim("M23/offsite_keeps_moving")
    scheduler.advance_and_flush(sim.world, 5)
    _m23_lunch(sim, veggie=True, classic_qty=1)
    cal_mut.create_event(sim.world.calendar, title="Team Lunch",
                         day="2026-05-22", start="19:00", end="20:00")
    for who in ("dana@example.com", "priya@example.com", "alex@example.com"):
        mail_mut.send_email(sim.world.mail, to=who, subject="Lunch",
                            body="Confirmed: team lunch at 7:00 PM today.")
    res = sim._probe()
    assert res["success"] is False
    assert "meeting_after_3pm_free" in res["missed_milestones"]
    assert "notified_dana" in res["missed_milestones"]
    assert "notified_attendees" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M24 (procurement puzzle): global-optimum trap — consolidate at ValueMart
# --------------------------------------------------------------------------- #

def _m24_buy_valuemart(sim: _CrossSim, pids, coupon=None) -> None:
    for pid in pids:
        market_mut.add_to_cart(sim.world.market, product_id=pid)
    if coupon:
        market_mut.apply_coupon(sim.world.market, coupon)
    market_mut.place_order(sim.world)


def test_m24_consolidate_valuemart_wins():
    """The optimum: all three at ValueMart with VALUE10 = $310.47 <= $320."""
    sim = _CrossSim("M24/procurement_puzzle")
    _m24_buy_valuemart(sim, ["vm_mouse_wireless", "vm_kb_mech", "vm_monitor_24"],
                       coupon="VALUE10")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m24_greedy_split_busts_budget():
    """Greedy per-item-cheapest splits stores (mouse+kb at ValueMart, monitor at
    ShopGym). No single ValueMart order has all three, so the items milestone
    misses — and the split total ($327.46) is over budget anyway."""
    sim = _CrossSim("M24/procurement_puzzle")
    _m24_buy_valuemart(sim, ["vm_mouse_wireless", "vm_kb_mech"], coupon="VALUE10")
    mutations.add_to_cart(sim.shop, "p_monitor_24", 1)
    mutations.place_order(sim.shop, "pay_visa")
    res = sim._probe()
    assert res["success"] is False
    assert "ordered_three_at_valuemart" in res["missed_milestones"]


def test_m24_no_coupon_over_budget():
    """Right three at ValueMart but no coupon -> $344.97 > $320."""
    sim = _CrossSim("M24/procurement_puzzle")
    _m24_buy_valuemart(sim, ["vm_mouse_wireless", "vm_kb_mech", "vm_monitor_24"])
    res = sim._probe()
    assert res["success"] is False
    assert "under_budget" in res["missed_milestones"]
    assert "applied_value10" in res["missed_milestones"]


def test_m24_wrong_item_decoy_fails():
    """Grabbed a lookalike (Wireless Keyboard) instead of the required Mechanical
    Keyboard -> the exact-set items milestone misses."""
    sim = _CrossSim("M24/procurement_puzzle")
    _m24_buy_valuemart(sim, ["vm_mouse_wireless", "vm_kb_wireless", "vm_monitor_24"],
                       coupon="VALUE10")
    res = sim._probe()
    assert res["success"] is False
    assert "ordered_three_at_valuemart" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M25 (dispatch desk): route each detail to the right person (+ stale value)
# --------------------------------------------------------------------------- #

def _m25_send(sim: _CrossSim, to: str, body: str) -> None:
    mail_mut.send_email(sim.world.mail, to=to, subject="update", body=body)


def test_m25_correction_fires_at_step_4():
    sim = _CrossSim("M25/dispatch_desk")
    assert not bus.has_delivered(sim.world, "DispatchCorrection")
    scheduler.advance_and_flush(sim.world, 4)
    assert bus.has_delivered(sim.world, "DispatchCorrection")
    corr = [e for e in sim.world.mail.inbox.values()
            if "dispatch-correction" in (e.labels or [])]
    assert len(corr) == 1 and "21,000" in corr[0].body


def test_m25_full_path_routes_all_four():
    sim = _CrossSim("M25/dispatch_desk")
    scheduler.advance_and_flush(sim.world, 4)
    _m25_send(sim, "priya@example.com", "The all-hands moved to 4:00 PM.")
    _m25_send(sim, "alex@example.com", "Your Q3 budget is $21,000.")  # corrected
    _m25_send(sim, "sam@example.com", "The report deadline is Friday.")
    _m25_send(sim, "dana@example.com", "Your new desk is B12.")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m25_stale_alex_budget_fails():
    """Relayed Alex's ORIGINAL $12,000 instead of the corrected $21,000."""
    sim = _CrossSim("M25/dispatch_desk")
    scheduler.advance_and_flush(sim.world, 4)
    _m25_send(sim, "priya@example.com", "The all-hands moved to 4:00 PM.")
    _m25_send(sim, "alex@example.com", "Your Q3 budget is $12,000.")  # STALE
    _m25_send(sim, "sam@example.com", "The report deadline is Friday.")
    _m25_send(sim, "dana@example.com", "Your new desk is B12.")
    res = sim._probe()
    assert res["success"] is False
    assert "notified_alex_budget" in res["missed_milestones"]


def test_m25_cross_wired_fails():
    """Sent Priya the budget and Alex the time (details swapped)."""
    sim = _CrossSim("M25/dispatch_desk")
    scheduler.advance_and_flush(sim.world, 4)
    _m25_send(sim, "priya@example.com", "Your Q3 budget is $21,000.")  # wrong detail
    _m25_send(sim, "alex@example.com", "The all-hands moved to 4:00 PM.")  # wrong
    _m25_send(sim, "sam@example.com", "The report deadline is Friday.")
    _m25_send(sim, "dana@example.com", "Your new desk is B12.")
    res = sim._probe()
    assert res["success"] is False
    assert "notified_priya_time" in res["missed_milestones"]
    assert "notified_alex_budget" in res["missed_milestones"]


def test_m25_replied_to_manager_only_fails():
    """The M22 trap at scale: dumped everything back to the manager instead of
    messaging each teammate directly."""
    sim = _CrossSim("M25/dispatch_desk")
    scheduler.advance_and_flush(sim.world, 4)
    _m25_send(sim, "manager@example.com",
              "Priya 4:00 PM; Alex $21,000; Sam Friday; Dana B12.")
    res = sim._probe()
    assert res["success"] is False
    for ms in ("notified_priya_time", "notified_alex_budget",
               "notified_sam_deadline", "notified_dana_desk"):
        assert ms in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# M26 (calendar purge): async destructive EXACT-SET delete with a kept exception
# --------------------------------------------------------------------------- #

def _m26_event_id(sim: _CrossSim, needle: str) -> str:
    for eid, ev in sim.world.calendar.events.items():
        if needle.lower() in (ev.title or "").lower():
            return eid
    raise KeyError(needle)


def _m26_delete(sim: _CrossSim, needle: str) -> None:
    cal_mut.delete_event(sim.world.calendar, _m26_event_id(sim, needle))


def test_m26_cancellation_fires_at_step_5():
    """Env-truth: the async cancellation lands at step 5, names the exception, and
    is genuinely learnable (body carries both 'Retro' and 'keep')."""
    sim = _CrossSim("M26/calendar_purge_async")
    assert not bus.has_delivered(sim.world, "ProjectCancelled")
    scheduler.advance_and_flush(sim.world, 5)
    assert bus.has_delivered(sim.world, "ProjectCancelled")
    cancels = [e for e in sim.world.mail.inbox.values()
               if "project-cancelled" in (e.labels or [])]
    assert len(cancels) == 1
    body = cancels[0].body.lower()
    assert "phoenix" in body and "retro" in body and "keep" in body


def test_m26_full_path_deletes_exactly_target():
    """Delete EXACTLY the two non-retro Phoenix meetings -> success, score 1.0.
    The kept Retro, the 1:1, and both Atlas decoys remain."""
    sim = _CrossSim("M26/calendar_purge_async")
    scheduler.advance_and_flush(sim.world, 5)
    _m26_delete(sim, "Phoenix Standup")
    _m26_delete(sim, "Phoenix Design Review")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0
    # Exactly the right four remain.
    remaining = {ev.title for ev in sim.world.calendar.events.values()}
    assert remaining == {"Atlas Sync", "1:1 with Manager",
                         "Phoenix Retro", "Atlas Planning"}


def test_m26_over_delete_retro_fails():
    """The engineered trap: pattern-matched 'delete ALL Phoenix' and removed the
    kept Retro too. Completeness fires; exact-set (precision) does not."""
    sim = _CrossSim("M26/calendar_purge_async")
    scheduler.advance_and_flush(sim.world, 5)
    _m26_delete(sim, "Phoenix Standup")
    _m26_delete(sim, "Phoenix Design Review")
    _m26_delete(sim, "Phoenix Retro")               # OVER-delete the exception
    res = sim._probe()
    assert res["success"] is False
    assert "deleted_exactly_target" in res["missed_milestones"]
    assert "deleted_all_target" not in res["missed_milestones"]  # completeness ok
    fired = {m["name"] for m in res["all_milestones"] if m["fired_at_step"] >= 0}
    assert "over_deleted_exception" in fired         # diagnostic gate fired
    assert res["score"] == 0.5


def test_m26_over_delete_decoy_fails():
    """Confused projects and removed an Atlas decoy along with the Phoenix two."""
    sim = _CrossSim("M26/calendar_purge_async")
    scheduler.advance_and_flush(sim.world, 5)
    _m26_delete(sim, "Phoenix Standup")
    _m26_delete(sim, "Phoenix Design Review")
    _m26_delete(sim, "Atlas Sync")                   # OVER-delete a decoy
    res = sim._probe()
    assert res["success"] is False
    assert "deleted_exactly_target" in res["missed_milestones"]


def test_m26_under_delete_fails():
    """Missed one of the two Phoenix meetings -> completeness never fires."""
    sim = _CrossSim("M26/calendar_purge_async")
    scheduler.advance_and_flush(sim.world, 5)
    _m26_delete(sim, "Phoenix Standup")              # only one of two
    res = sim._probe()
    assert res["success"] is False
    assert "deleted_all_target" in res["missed_milestones"]
    assert "deleted_exactly_target" in res["missed_milestones"]
    assert res["score"] == 0.0


def test_m26_never_acted_fails():
    """Never noticed the async email / deleted nothing -> zero credit."""
    sim = _CrossSim("M26/calendar_purge_async")
    scheduler.advance_and_flush(sim.world, 5)
    res = sim._probe()
    assert res["success"] is False
    assert res["score"] == 0.0


def test_m26_read_email_fires_read_level():
    """4-level facts: opening the cancellation email flips the (weight-0) read
    gate, distinguishing 'noticed it' from 'acted blind'."""
    sim = _CrossSim("M26/calendar_purge_async")
    scheduler.advance_and_flush(sim.world, 5)
    cancel = next(e for e in sim.world.mail.inbox.values()
                  if "project-cancelled" in (e.labels or []))
    mail_mut.mark_read(sim.world.mail, cancel.id)
    res = sim._probe()
    fired = {m["name"] for m in res["all_milestones"] if m["fired_at_step"] >= 0}
    assert "read_cancellation_email" in fired
    assert "cancellation_email_delivered" in fired


# --------------------------------------------------------------------------- #
# M27 (budget desk): sequential running-total reconciliation + async raise
# --------------------------------------------------------------------------- #

def _m27_reply(sim: _CrossSim, oid: str, verdict: str) -> None:
    """Send a customer reply that the verifier matches: order id in subject/body
    + 'approved' or 'deferred' keyword. verdict in {'approve','defer'}."""
    body = (f"Order {oid} approved — refund processed." if verdict == "approve"
            else f"Order {oid} deferred to tomorrow.")
    mail_mut.send_email(sim.world.mail,
                        to=f"{oid.lower().replace('-', '')}@customers.com",
                        subject=f"Re: Refund request — {oid}", body=body)


# The FINAL correct approved set (post-raise, $300 budget): the oldest-first
# prefix 45+60+55+50+30+40 = 280 <= 300; next (REF-07, $35) -> 315 > 300, stop.
_M27_APPROVE = ["REF-01", "REF-02", "REF-03", "REF-04", "REF-05", "REF-06"]


def test_m27_raise_fires_at_step_8():
    sim = _CrossSim("M27/budget_desk")
    assert not bus.has_delivered(sim.world, "RefundBudgetRaised")
    scheduler.advance_and_flush(sim.world, 8)
    assert bus.has_delivered(sim.world, "RefundBudgetRaised")
    raises = [e for e in sim.world.mail.inbox.values()
              if "budget-raise" in (e.labels or [])]
    assert len(raises) == 1 and "300" in raises[0].body


def test_m27_full_path_scores_one():
    """Approve exactly the $300 prefix {REF-01..06} -> success, 1.0."""
    sim = _CrossSim("M27/budget_desk")
    scheduler.advance_and_flush(sim.world, 8)        # raise lands -> budget 300
    for oid in _M27_APPROVE:
        _m27_reply(sim, oid, "approve")
    res = sim._probe()
    assert res["success"] is True
    assert res["score"] == 1.0


def test_m27_ignored_raise_underapproves_fails():
    """Stuck on the original $200 cap -> approved only {01,02,03} -> incomplete."""
    sim = _CrossSim("M27/budget_desk")
    scheduler.advance_and_flush(sim.world, 8)
    for oid in ["REF-01", "REF-02", "REF-03"]:
        _m27_reply(sim, oid, "approve")
    res = sim._probe()
    assert res["success"] is False
    assert "approved_all_correct" in res["missed_milestones"]
    assert "approved_exactly_correct" in res["missed_milestones"]


def test_m27_greedy_overapprove_busts_budget_fails():
    """Approved every eligible request, ignoring the running budget -> over the
    cap. Completeness fires, exact does not; the over-budget diagnostic fires."""
    sim = _CrossSim("M27/budget_desk")
    scheduler.advance_and_flush(sim.world, 8)
    for oid in ["REF-01", "REF-02", "REF-03", "REF-04", "REF-05", "REF-06",
                "REF-07", "REF-08", "REF-13"]:
        _m27_reply(sim, oid, "approve")
    res = sim._probe()
    assert res["success"] is False
    assert "approved_exactly_correct" in res["missed_milestones"]
    assert "approved_all_correct" not in res["missed_milestones"]   # completeness ok
    fired = {m["name"] for m in res["all_milestones"] if m["fired_at_step"] >= 0}
    assert "over_budget_approved" in fired
    assert res["score"] == 0.4


def test_m27_approve_urgent_ineligible_fails():
    """Yielded to the URGENT shipped request (REF-12, ineligible) on top of the
    correct set -> over-approve; the ineligible diagnostic fires."""
    sim = _CrossSim("M27/budget_desk")
    scheduler.advance_and_flush(sim.world, 8)
    for oid in _M27_APPROVE + ["REF-12"]:
        _m27_reply(sim, oid, "approve")
    res = sim._probe()
    assert res["success"] is False
    assert "approved_exactly_correct" in res["missed_milestones"]
    fired = {m["name"] for m in res["all_milestones"] if m["fired_at_step"] >= 0}
    assert "approved_an_ineligible" in fired


def test_m27_approve_vip_over_cutoff_fails():
    """Approved the salient $200 VIP (REF-13), which is eligible but beyond the
    cutoff -> over-approve, exact fails."""
    sim = _CrossSim("M27/budget_desk")
    scheduler.advance_and_flush(sim.world, 8)
    for oid in _M27_APPROVE + ["REF-13"]:
        _m27_reply(sim, oid, "approve")
    res = sim._probe()
    assert res["success"] is False
    assert "approved_exactly_correct" in res["missed_milestones"]


def test_m27_no_credit_before_raise():
    """Stickiness guard: matching the pre-raise $200 prefix {01,02,03} must NOT
    score success before the budget raise delivers (grading is gated on it)."""
    sim = _CrossSim("M27/budget_desk")
    scheduler.advance_and_flush(sim.world, 5)        # before the step-8 raise
    for oid in ["REF-01", "REF-02", "REF-03"]:
        _m27_reply(sim, oid, "approve")
    res = sim._probe()
    assert res["success"] is False
    assert "approved_all_correct" in res["missed_milestones"]
    assert "approved_exactly_correct" in res["missed_milestones"]


# --------------------------------------------------------------------------- #
# Backward-compat: probe.state still aliases the shop GymState
# --------------------------------------------------------------------------- #

def test_probe_state_aliases_world_shop():
    sim = _CrossSim("M2/order_then_track_via_email")
    assert sim.world.shop is sim.shop
