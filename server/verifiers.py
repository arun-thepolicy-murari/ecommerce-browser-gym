"""Per-step milestone verifier.

Each task is defined as an ORDERED LIST OF MILESTONES. A milestone is a
weighted predicate over the gym state and the current URL. After every
agent action, the harness probes the milestone list and awards credit
for any milestone that has just become satisfied.

Why ordered milestones (not free-form assertions)?
- The agent should achieve them in order to complete a real user
  journey ("logged in" before "added to cart" before "place_order").
- Awarding them in order means partial progress is meaningful — a
  half-completed task gets a half-credit score, with a clear failure
  point (where did the agent stop?).
- Each milestone records its first-fired step so we can reconstruct
  the agent's progression in the trajectory file.

The harness queries this in two places:
  1. After every action — to detect newly-satisfied milestones (live
     progress monitoring).
  2. At episode end — to compute the final aggregated score.

This pattern is what production browser-agent benchmarks (WebArena,
VisualWebArena, Mind2Web, BrowserGym) actually use. The novelty here
is using it on a stateful in-house simulator so milestone checks can
inspect backend state, not just DOM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

from server.state import GymState

if TYPE_CHECKING:
    from server.apps.world import WorldState


# --------------------------------------------------------------------------- #
# Probe — the snapshot a milestone check sees on each evaluation
# --------------------------------------------------------------------------- #

@dataclass
class Probe:
    """All the information a milestone check can use to evaluate itself.

    ``state`` is always the shop ``GymState`` — so every existing single-app
    milestone (which reads ``probe.state.*``) is UNCHANGED. Cross-app
    episodes additionally carry the whole multi-app ``world`` (every per-app
    store + the append-only event log) and ``initial_world``; cross-app
    milestones read those. ``active_tab_url`` is the URL of the focused tab
    in a multi-tab episode (defaults to ``url`` for single-tab)."""
    state: GymState
    url: str                                      # current browser URL
    initial_state: GymState                       # snapshot at episode start
    world: "WorldState | None" = None
    initial_world: "WorldState | None" = None
    active_tab_url: str = ""


# --------------------------------------------------------------------------- #
# Milestone
# --------------------------------------------------------------------------- #

@dataclass
class Milestone:
    """One checkpoint along the agent's path to task completion.

    A milestone is purely a SCORING unit: a weighted predicate that
    fires once, the first time it becomes true. Milestones intentionally
    no longer carry a per-task `failure_category` label — that approach
    was task-coupled and didn't generalize to novel tasks. Failure
    classification now happens at the trajectory level via the universal
    taxonomy in ``harness/failure_classifier.py``.

    Attributes:
        name:               Human-readable identifier (used in details +
                            for debugging which scoring unit was missed).
        weight:             Contribution to final score (sum across all
                            milestones in a task should = 1.0).
        check:              ``(probe) -> bool``. The predicate.
        required_for_success:
                            If True, missing this means the episode
                            cannot be marked ``success=True`` regardless
                            of score (goal-defining milestones).
        fired_at_step:      Set by the harness when the milestone first
                            evaluates to True. Default -1 = never.
        category:           Optional grouping string (analytics only).
    """
    name: str
    weight: float
    check: Callable[[Probe], bool]
    required_for_success: bool = False
    fired_at_step: int = -1
    category: str = ""


# --------------------------------------------------------------------------- #
# Suite — the per-task milestone list
# --------------------------------------------------------------------------- #

@dataclass
class TaskSuite:
    task_id: str
    milestones: list[Milestone] = field(default_factory=list)

    def evaluate(self, probe: Probe, current_step: int) -> dict[str, Any]:
        """Probe every milestone. For any that fire for the first time,
        mark fired_at_step. Return a summary dict (which milestones just
        fired, aggregated score, success).

        Failure CLASSIFICATION is no longer done here — it happens once
        per episode at the trajectory level via
        ``harness/failure_classifier.classify``. The verifier's job is
        purely scoring + success determination. ``missed_milestones``
        is still surfaced for debugging which scoring unit didn't fire.
        """
        newly_fired: list[str] = []
        for m in self.milestones:
            if m.fired_at_step >= 0:
                continue
            try:
                ok = bool(m.check(probe))
            except Exception:
                ok = False
            if ok:
                m.fired_at_step = current_step
                newly_fired.append(m.name)

        return {
            "score":   self.aggregate_score(),
            "success": self.is_success(),
            "newly_fired": newly_fired,
            "missed_milestones": [
                m.name for m in self.milestones if m.fired_at_step < 0
            ],
            "all_milestones": [
                {"name": m.name, "weight": m.weight,
                 "fired_at_step": m.fired_at_step,
                 "required": m.required_for_success}
                for m in self.milestones
            ],
        }

    def aggregate_score(self) -> float:
        total_w = sum(m.weight for m in self.milestones) or 1.0
        earned = sum(m.weight for m in self.milestones
                     if m.fired_at_step >= 0)
        return round(earned / total_w, 4)

    def is_success(self) -> bool:
        """All required milestones must have fired AND total score == 1.0."""
        for m in self.milestones:
            if m.required_for_success and m.fired_at_step < 0:
                return False
        return self.aggregate_score() >= 0.999


# --------------------------------------------------------------------------- #
# Helpers used by checks
# --------------------------------------------------------------------------- #

def _on_url(probe: Probe, *substrs: str) -> bool:
    return any(s in probe.url for s in substrs)


def _order_with(probe: Probe, *,
                product_ids: tuple[str, ...] | None = None,
                variant_id: str | None = None,
                exclude_product_ids: tuple[str, ...] = (),
                exactly_n_items: int | None = None,
                ) -> bool:
    """Returns True iff an order exists with the requested shape."""
    for o in probe.state.orders.values():
        if exactly_n_items is not None and len(o.items) != exactly_n_items:
            continue
        if exclude_product_ids:
            if any(it.product_id in exclude_product_ids for it in o.items):
                continue
        if product_ids:
            present = {it.product_id for it in o.items}
            if not set(product_ids).issubset(present):
                continue
        if variant_id is not None:
            if not any(it.variant_id == variant_id for it in o.items):
                continue
        return True
    return False


def _newest_order(probe: Probe):
    if not probe.state.orders:
        return None
    return max(probe.state.orders.values(),
               key=lambda o: o.placed_at)


def _log_has(probe: Probe, kind: str, **fields: Any) -> bool:
    """True if the action_log contains an event of `kind` whose fields
    all match. Used by taxonomy-navigation verifiers to confirm the
    agent browsed categories/subcategories rather than searching."""
    for e in probe.state.action_log:
        if e.get("kind") != kind:
            continue
        if all(e.get(k) == v for k, v in fields.items()):
            return True
    return False


def _log_count(probe: Probe, kind: str) -> int:
    return sum(1 for e in probe.state.action_log if e.get("kind") == kind)


# --------------------------------------------------------------------------- #
# Per-task suite builders
# --------------------------------------------------------------------------- #

# --- A1: buy_wireless_mouse ---

def _suite_a1() -> TaskSuite:
    target = "p_mouse_wireless"
    # The catalog has multiple "wireless" mice; reject ANY non-target mouse.
    # Updated when the catalog grew (May 2026) — was just p_mouse_gaming.
    mouse_distractors = (
        "p_mouse_gaming",
        "p_mouse_ergonomic",
        "p_mouse_mini",
        "p_mouse_trackpad",
    )
    return TaskSuite(
        task_id="A1/buy_wireless_mouse",
        milestones=[
            Milestone("viewed_product_page", weight=0.15,
                      check=lambda p: _on_url(p, "/product/p_mouse_wireless")),
            Milestone("added_target_to_cart", weight=0.20,
                      check=lambda p: any(
                          it.product_id == target
                          for it in p.state.cart.items
                      ) or any(
                          it.product_id == target
                          for o in p.state.orders.values()
                          for it in o.items
                      )),
            Milestone("avoided_all_distractors", weight=0.10,
                      check=lambda p: not any(
                          it.product_id in mouse_distractors
                          for o in p.state.orders.values()
                          for it in o.items
                      )),
            Milestone("reached_checkout", weight=0.10,
                      check=lambda p: _on_url(p, "/checkout")),
            Milestone("order_placed", weight=0.30,
                      check=lambda p: _order_with(
                          p, product_ids=(target,), exactly_n_items=1,
                          exclude_product_ids=mouse_distractors,
                      ),
                      required_for_success=True),
            Milestone("on_confirmation_page", weight=0.10,
                      check=lambda p: _on_url(p, "/order/")),
            Milestone("home_address_used", weight=0.05,
                      check=lambda p: (
                          _newest_order(p) is not None
                          and all(
                              it.ship_to_address_id == "addr_home"
                              for it in _newest_order(p).items
                          )
                      )),
        ],
    )


# --- A2: filter_laptop ---

def _suite_a2() -> TaskSuite:
    return TaskSuite(
        task_id="A2/filter_laptop",
        milestones=[
            Milestone("searched_or_filtered_laptops", weight=0.20,
                      check=lambda p: (
                          _on_url(p, "/search")
                          or _on_url(p, "/category/electronics")
                      )),
            Milestone("viewed_an_electronics_laptop", weight=0.15,
                      check=lambda p: any(
                          s in p.url for s in (
                              "/product/p_laptop_studio",
                              "/product/p_laptop_pro",
                              "/product/p_laptop_budget",
                              # New laptops added May 2026; viewing them
                              # counts as exploration but they won't
                              # satisfy the rating/price constraints.
                              "/product/p_laptop_studio_pro",
                              "/product/p_laptop_creator",
                          )
                      )),
            Milestone("ordered_a_laptop", weight=0.30,
                      check=lambda p: any(
                          ("laptop" in p.state.products[it.product_id].name.lower()
                           and p.state.products[it.product_id].category == "electronics")
                          for o in p.state.orders.values()
                          for it in o.items
                      ),
                      required_for_success=True),
            Milestone("under_1000_subtotal", weight=0.20,
                      check=lambda p: (
                          _newest_order(p) is not None
                          and _newest_order(p).subtotal < 1000.0
                      )),
            Milestone("ordered_product_rating_ge_45", weight=0.15,
                      check=lambda p: all(
                          p.state.products[it.product_id].rating >= 4.5
                          for it in (_newest_order(p).items
                                     if _newest_order(p) else [])
                      ) and _newest_order(p) is not None),
        ],
    )


# --- A3: configure_bundle ---

def _suite_a3() -> TaskSuite:
    return TaskSuite(
        task_id="A3/configure_bundle",
        milestones=[
            Milestone("opened_variant_picker_on_laptop", weight=0.10,
                      check=lambda p: any(
                          s in p.url for s in (
                              "/product/p_laptop_studio",
                              "/product/p_laptop_pro",
                          )
                      )),
            Milestone("ordered_correct_laptop_variant", weight=0.25,
                      check=lambda p: any(
                          it.variant_id == "v_lt_32_1tb"
                          for o in p.state.orders.values()
                          for it in o.items
                      ),
                      required_for_success=True),
            Milestone("ordered_wireless_mouse", weight=0.15,
                      check=lambda p: _order_with(
                          p, product_ids=("p_mouse_wireless",),
                      )),
            Milestone("ordered_mechanical_keyboard", weight=0.15,
                      check=lambda p: _order_with(
                          p, product_ids=("p_kb_mech",),
                      )),
            Milestone("subtotal_under_1900", weight=0.20,
                      check=lambda p: (
                          _newest_order(p) is not None
                          and _newest_order(p).subtotal < 1900.0
                      )),
            Milestone("three_items_in_order", weight=0.10,
                      check=lambda p: _order_with(
                          p, exactly_n_items=3,
                      ),
                      required_for_success=True),
            Milestone("on_confirmation_page", weight=0.05,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --- B1: add_address ---

def _suite_b1() -> TaskSuite:
    return TaskSuite(
        task_id="B1/add_address",
        milestones=[
            Milestone("navigated_to_addresses", weight=0.20,
                      check=lambda p: _on_url(
                          p, "/account/addresses",
                      )),
            Milestone("address_added", weight=0.30,
                      check=lambda p: (
                          p.state.current_user_id is not None
                          and any(
                              a.label.lower() == "beach house"
                              for a in p.state.users[p.state.current_user_id].addresses.values()
                          )
                      ),
                      required_for_success=True),
            Milestone("address_fields_correct", weight=0.20,
                      check=lambda p: (
                          p.state.current_user_id is not None
                          and any(
                              (a.label.lower() == "beach house"
                               and "ocean drive" in a.line1.lower()
                               and a.city.lower() == "montauk"
                               and a.zip == "11954")
                              for a in p.state.users[p.state.current_user_id].addresses.values()
                          )
                      )),
            Milestone("address_set_as_default", weight=0.30,
                      check=lambda p: (
                          p.state.current_user_id is not None
                          and any(
                              (a.label.lower() == "beach house" and a.is_default)
                              for a in p.state.users[p.state.current_user_id].addresses.values()
                          )
                      ),
                      required_for_success=True),
        ],
    )


# --- B2: track_and_return ---

def _suite_b2() -> TaskSuite:
    return TaskSuite(
        task_id="B2/track_and_return",
        milestones=[
            Milestone("navigated_to_orders", weight=0.15,
                      check=lambda p: _on_url(
                          p, "/account/orders",
                      )),
            Milestone("opened_order_detail", weight=0.15,
                      check=lambda p: _on_url(
                          p, "/account/orders/ORD-EXISTING-1234",
                      )),
            Milestone("opened_tracking_modal", weight=0.15,
                      check=lambda p: any(
                          e.get("kind") == "viewed_tracking"
                          for e in p.state.action_log
                      )),
            Milestone("return_initiated", weight=0.25,
                      check=lambda p: any(
                          r.order_id == "ORD-EXISTING-1234"
                          for r in p.state.returns.values()
                      ),
                      required_for_success=True),
            Milestone("return_is_for_mouse_only", weight=0.20,
                      check=lambda p: any(
                          (r.order_id == "ORD-EXISTING-1234"
                           and r.item_ids == ["ln_mouse"])
                          for r in p.state.returns.values()
                      ),
                      required_for_success=True),
            Milestone("return_reason_defective", weight=0.05,
                      check=lambda p: any(
                          (r.order_id == "ORD-EXISTING-1234"
                           and r.reason == "defective")
                          for r in p.state.returns.values()
                      )),
            Milestone("refund_method_original_payment", weight=0.05,
                      check=lambda p: any(
                          (r.order_id == "ORD-EXISTING-1234"
                           and r.refund_method == "original_payment")
                          for r in p.state.returns.values()
                      )),
        ],
    )


# --- B3: account_overhaul ---

def _suite_b3() -> TaskSuite:
    def _has_default_work(p: Probe) -> bool:
        if p.state.current_user_id is None:
            return False
        u = p.state.users[p.state.current_user_id]
        a = u.addresses.get("addr_work")
        return a is not None and a.is_default

    def _has_backup_card_default(p: Probe) -> bool:
        if p.state.current_user_id is None:
            return False
        u = p.state.users[p.state.current_user_id]
        return any(
            (pm.nickname == "Backup Card" or pm.label == "Backup Card"
             or "backup" in pm.label.lower())
            and pm.is_default
            for pm in u.payment_methods.values()
        )

    def _two_fa_enabled(p: Probe) -> bool:
        if p.state.current_user_id is None:
            return False
        return p.state.users[p.state.current_user_id].two_fa_enabled

    return TaskSuite(
        task_id="B3/account_overhaul",
        milestones=[
            Milestone("navigated_to_account", weight=0.10,
                      check=lambda p: _on_url(p, "/account")),
            Milestone("set_work_as_default_address", weight=0.30,
                      check=_has_default_work,
                      required_for_success=True),
            Milestone("backup_card_added_and_default", weight=0.30,
                      check=_has_backup_card_default,
                      required_for_success=True),
            Milestone("two_fa_enabled", weight=0.30,
                      check=_two_fa_enabled,
                      required_for_success=True),
        ],
    )


# --- C1: promo_partial ---

def _suite_c1() -> TaskSuite:
    def _order_has_both(p: Probe) -> bool:
        return _order_with(
            p, product_ids=("p_laptop_studio", "p_clothing_tshirt"),
        )

    def _used_correct_promo(p: Probe) -> bool:
        o = _newest_order(p)
        return o is not None and o.promo_code == "TECH20"

    def _discount_matches_20pct_of_laptop_only(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None or o.promo_code != "TECH20":
            return False
        laptop_total = sum(
            it.unit_price * it.quantity
            for it in o.items
            if p.state.products[it.product_id].category == "electronics"
        )
        expected = round(laptop_total * 0.20, 2)
        return abs(o.discount - expected) <= 0.05

    return TaskSuite(
        task_id="C1/promo_partial",
        milestones=[
            Milestone("both_items_in_order", weight=0.25,
                      check=_order_has_both,
                      required_for_success=True),
            Milestone("tech20_applied", weight=0.30,
                      check=_used_correct_promo,
                      required_for_success=True),
            Milestone("discount_is_20pct_of_laptop_only", weight=0.30,
                      check=_discount_matches_20pct_of_laptop_only,
                      required_for_success=True),
            Milestone("on_confirmation_page", weight=0.15,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --- C2: split_shipping_gift ---

def _suite_c2() -> TaskSuite:
    def _two_shipments(p: Probe) -> bool:
        o = _newest_order(p)
        return o is not None and len(o.shipments) == 2

    def _hp_home_with_giftwrap(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id == "p_hp_studio"
             and it.ship_to_address_id == "addr_home"
             and it.gift_wrap is True
             and "happy birthday" in (it.gift_message or "").lower())
            for it in o.items
        )

    def _mouse_work_no_giftwrap(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id == "p_mouse_wireless"
             and it.ship_to_address_id == "addr_work"
             and it.gift_wrap is False)
            for it in o.items
        )

    return TaskSuite(
        task_id="C2/split_shipping_gift",
        milestones=[
            Milestone("two_items_ordered", weight=0.15,
                      check=lambda p: _order_with(
                          p, product_ids=("p_hp_studio", "p_mouse_wireless"),
                          exactly_n_items=2,
                      ),
                      required_for_success=True),
            Milestone("headphones_home_with_giftwrap", weight=0.30,
                      check=_hp_home_with_giftwrap,
                      required_for_success=True),
            Milestone("mouse_work_no_giftwrap", weight=0.25,
                      check=_mouse_work_no_giftwrap,
                      required_for_success=True),
            Milestone("two_shipments_in_confirmation", weight=0.20,
                      check=_two_shipments,
                      required_for_success=True),
            Milestone("on_confirmation_page", weight=0.10,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --- C3: subscription_loyalty ---

def _suite_c3() -> TaskSuite:
    def _has_subscription(p: Probe) -> bool:
        return any(
            (s.product_id == "p_pet_food"
             and s.cadence == "weekly"
             and s.deliveries_remaining == 4)
            for s in p.state.subscriptions.values()
        )

    def _loyalty_discount_set(p: Probe) -> bool:
        return any(
            (s.product_id == "p_pet_food"
             and abs(s.loyalty_discount_pct - 0.10) < 0.001)
            for s in p.state.subscriptions.values()
        )

    return TaskSuite(
        task_id="C3/subscription_loyalty",
        milestones=[
            Milestone("on_pet_food_product_page", weight=0.10,
                      check=lambda p: _on_url(
                          p, "/product/p_pet_food",
                      )),
            Milestone("subscription_created", weight=0.40,
                      check=_has_subscription,
                      required_for_success=True),
            Milestone("loyalty_10pct_recorded", weight=0.30,
                      check=_loyalty_discount_set,
                      required_for_success=True),
            Milestone("on_subscription_confirmation", weight=0.20,
                      check=lambda p: _on_url(p, "/account/subscriptions")),
        ],
    )


# --------------------------------------------------------------------------- #
# VERY HARD tasks — added May 2026. Heavy adversarial pressure + multi-step
# state inspection.
# --------------------------------------------------------------------------- #

# --- A4: home_office_bundle ---

def _suite_a4() -> TaskSuite:
    """4-item bundle: 27" monitor + mechanical keyboard + ergonomic mouse
    + USB-C charger. All electronics, subtotal < $550, ship to Work, pay
    PayPal. Heavy distractor pressure (multiple mice, multiple keyboards,
    Office Display masquerading as electronics)."""

    REQUIRED_PRODUCTS = {
        "p_monitor_27",           # 27" — NOT p_monitor_24
        "p_kb_mech",              # mechanical — NOT p_kb_mini / p_kb_wireless / p_kb_membrane
        "p_mouse_ergonomic",      # ergonomic — NOT p_mouse_wireless / p_mouse_gaming
        "p_charger",
    }
    FORBIDDEN_PRODUCTS = {
        "p_monitor_24",          # 24" — wrong size
        "p_office_display",      # office category, not electronics
        "p_kb_wireless", "p_kb_mini", "p_kb_membrane",  # wrong keyboards
        "p_mouse_wireless", "p_mouse_gaming", "p_mouse_mini", "p_mouse_trackpad",
    }

    def _has_all_required(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        present = {it.product_id for it in o.items}
        return REQUIRED_PRODUCTS.issubset(present)

    def _no_forbidden(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return not any(it.product_id in FORBIDDEN_PRODUCTS for it in o.items)

    def _exactly_four_items(p: Probe) -> bool:
        o = _newest_order(p)
        return o is not None and len(o.items) == 4

    def _all_electronics(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return all(
            p.state.products[it.product_id].category == "electronics"
            for it in o.items
        )

    def _subtotal_under_550(p: Probe) -> bool:
        o = _newest_order(p)
        return o is not None and o.subtotal < 550.0

    def _shipped_to_work(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return all(
            it.ship_to_address_id == "addr_work"
            for it in o.items
        )

    def _paid_with_paypal(p: Probe) -> bool:
        o = _newest_order(p)
        return o is not None and o.payment_id == "pay_paypal"

    return TaskSuite(
        task_id="A4/home_office_bundle",
        milestones=[
            Milestone("all_four_required_items", weight=0.20,
                      check=_has_all_required, required_for_success=True),
            Milestone("no_forbidden_distractor", weight=0.15,
                      check=_no_forbidden),
            Milestone("exactly_four_line_items", weight=0.10,
                      check=_exactly_four_items),
            Milestone("all_items_electronics_category", weight=0.10,
                      check=_all_electronics),
            Milestone("subtotal_under_550", weight=0.15,
                      check=_subtotal_under_550),
            Milestone("shipped_to_work_address", weight=0.10,
                      check=_shipped_to_work),
            Milestone("paid_with_paypal", weight=0.10,
                      check=_paid_with_paypal),
            Milestone("on_confirmation_page", weight=0.10,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --- B4: subscription_juggle ---

def _suite_b4() -> TaskSuite:
    """Four parallel account changes:
      (1) Cancel the active Dog Food subscription
      (2) Create a new Dog TREATS subscription (biweekly, 6, Work, PayPal)
      (3) Enable 2FA
      (4) Initiate return on speaker only from the existing order
    """

    def _dogfood_cancelled(p: Probe) -> bool:
        sub = p.state.subscriptions.get("sub_existing_dogfood")
        return sub is not None and sub.status == "cancelled"

    def _new_treats_subscription(p: Probe) -> bool:
        return any(
            (s.product_id == "p_pet_treats"
             and s.cadence == "biweekly"
             and s.deliveries_remaining == 6
             and s.address_id == "addr_work"
             and s.payment_id == "pay_paypal"
             and s.status == "active")
            for s in p.state.subscriptions.values()
        )

    def _two_fa_on(p: Probe) -> bool:
        if p.state.current_user_id is None:
            return False
        return p.state.users[p.state.current_user_id].two_fa_enabled

    def _speaker_return_only(p: Probe) -> bool:
        return any(
            (r.order_id == "ORD-B4-9999"
             and r.item_ids == ["ln_speaker"]
             and r.reason == "changed_mind"
             and r.refund_method == "store_credit")
            for r in p.state.returns.values()
        )

    def _no_mouse_in_return(p: Probe) -> bool:
        return not any(
            (r.order_id == "ORD-B4-9999" and "ln_mouse" in r.item_ids)
            for r in p.state.returns.values()
        )

    return TaskSuite(
        task_id="B4/subscription_juggle",
        milestones=[
            Milestone("dogfood_sub_cancelled", weight=0.20,
                      check=_dogfood_cancelled,
                      required_for_success=True),
            Milestone("dog_treats_sub_created_correctly", weight=0.30,
                      check=_new_treats_subscription,
                      required_for_success=True),
            Milestone("two_fa_enabled", weight=0.15,
                      check=_two_fa_on,
                      required_for_success=True),
            Milestone("speaker_only_return_with_correct_options", weight=0.25,
                      check=_speaker_return_only,
                      required_for_success=True),
            Milestone("avoided_returning_mouse", weight=0.10,
                      check=_no_mouse_in_return),
        ],
    )


# --- C4: mega_checkout ---

def _suite_c4() -> TaskSuite:
    """The hardest checkout task. 3 items with 3 different shipping
    configurations + variant selection on t-shirt + promo + non-default
    payment. Combines C1 + C2 patterns into one episode."""

    def _has_all_three(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        present = {it.product_id for it in o.items}
        return {"p_laptop_studio", "p_clothing_tshirt", "p_mouse_wireless"}.issubset(present)

    def _no_distractors(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        forbidden = {
            "p_laptop_studio_pro", "p_laptop_pro", "p_laptop_budget",
            "p_mouse_gaming", "p_mouse_ergonomic", "p_mouse_mini", "p_mouse_trackpad",
            "p_clothing_polo", "p_clothing_long_sleeve",
            "p_clothing_graphic", "p_clothing_tank", "p_clothing_hoodie",
        }
        return not any(it.product_id in forbidden for it in o.items)

    def _tshirt_size_m_black(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id == "p_clothing_tshirt"
             and it.variant_id == "v_ts_m_blk")
            for it in o.items
        )

    def _laptop_to_work(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id == "p_laptop_studio"
             and it.ship_to_address_id == "addr_work")
            for it in o.items
        )

    def _tshirt_home_giftwrap_message(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id == "p_clothing_tshirt"
             and it.ship_to_address_id == "addr_home"
             and it.gift_wrap is True
             and "happy birthday" in (it.gift_message or "").lower()
             and "mom" in (it.gift_message or "").lower())
            for it in o.items
        )

    def _mouse_home_no_giftwrap(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id == "p_mouse_wireless"
             and it.ship_to_address_id == "addr_home"
             and it.gift_wrap is False)
            for it in o.items
        )

    def _tech20_applied_correctly(p: Probe) -> bool:
        """TECH20 = 20% off electronics. In C4 there are TWO electronics
        items (laptop + wireless mouse), so the expected discount is
        20% of the sum of BOTH. The t-shirt (clothing) is not eligible."""
        o = _newest_order(p)
        if o is None or o.promo_code != "TECH20":
            return False
        electronics_total = sum(
            it.unit_price * it.quantity
            for it in o.items
            if p.state.products[it.product_id].category == "electronics"
        )
        expected = round(electronics_total * 0.20, 2)
        return abs(o.discount - expected) <= 0.05

    def _paid_with_visa(p: Probe) -> bool:
        o = _newest_order(p)
        return o is not None and o.payment_id == "pay_visa"

    return TaskSuite(
        task_id="C4/mega_checkout",
        milestones=[
            Milestone("all_three_required_items", weight=0.15,
                      check=_has_all_three, required_for_success=True),
            Milestone("no_distractor_picked", weight=0.10,
                      check=_no_distractors),
            Milestone("tshirt_size_m_black", weight=0.10,
                      check=_tshirt_size_m_black),
            Milestone("laptop_shipped_to_work", weight=0.10,
                      check=_laptop_to_work),
            Milestone("tshirt_home_with_giftwrap_message", weight=0.15,
                      check=_tshirt_home_giftwrap_message),
            Milestone("mouse_home_no_giftwrap", weight=0.10,
                      check=_mouse_home_no_giftwrap),
            Milestone("tech20_discount_on_all_electronics", weight=0.15,
                      check=_tech20_applied_correctly,
                      required_for_success=True),
            Milestone("paid_with_visa", weight=0.05,
                      check=_paid_with_visa),
            Milestone("on_confirmation_page", weight=0.10,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --------------------------------------------------------------------------- #
# Category D: taxonomy navigation
# --------------------------------------------------------------------------- #

# --- D1: browse_audio_no_search ---

def _suite_d1() -> TaskSuite:
    """Browse Audio -> headphones, pick a 4.5+ pair, WITHOUT the search bar."""
    QUALIFYING_HP = {"p_hp_premium", "p_hp_studio", "p_hp_studio_pro"}  # rating >= 4.5

    def _ordered_qualifying_hp(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return False
        return any(
            (it.product_id in QUALIFYING_HP
             and p.state.products[it.product_id].rating >= 4.5)
            for it in o.items
        )

    return TaskSuite(
        task_id="D1/browse_audio_no_search",
        milestones=[
            Milestone("visited_audio_category", weight=0.20,
                      check=lambda p: _log_has(p, "view_category", category="audio"),
                      required_for_success=True),
            Milestone("browsed_headphones_subcategory", weight=0.20,
                      check=lambda p: _log_has(p, "view_subcategory",
                                               category="audio", sub="headphones")),
            Milestone("avoided_search_bar", weight=0.15,
                      check=lambda p: _log_count(p, "search") == 0),
            Milestone("ordered_qualifying_headphone", weight=0.35,
                      check=_ordered_qualifying_hp,
                      required_for_success=True),
            Milestone("on_confirmation_page", weight=0.10,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --- D2: drill_electronics_keyboards ---

def _suite_d2() -> TaskSuite:
    """Drill Electronics -> keyboards subcategory, buy the mechanical one
    (p_kb_mech), avoiding the membrane keyboard. Browse, don't search."""

    def _ordered_mechanical(p: Probe) -> bool:
        return _order_with(p, product_ids=("p_kb_mech",))

    def _avoided_membrane(p: Probe) -> bool:
        o = _newest_order(p)
        if o is None:
            return True  # nothing ordered yet → hasn't picked the wrong one
        return not any(it.product_id == "p_kb_membrane" for it in o.items)

    return TaskSuite(
        task_id="D2/drill_electronics_keyboards",
        milestones=[
            Milestone("visited_electronics_category", weight=0.15,
                      check=lambda p: _log_has(p, "view_category",
                                               category="electronics"),
                      required_for_success=True),
            Milestone("drilled_keyboards_subcategory", weight=0.25,
                      check=lambda p: _log_has(p, "view_subcategory",
                                               category="electronics",
                                               sub="keyboards"),
                      required_for_success=True),
            Milestone("avoided_search_bar", weight=0.15,
                      check=lambda p: _log_count(p, "search") == 0),
            Milestone("ordered_mechanical_keyboard", weight=0.30,
                      check=_ordered_mechanical,
                      required_for_success=True),
            Milestone("avoided_membrane_keyboard", weight=0.05,
                      check=_avoided_membrane),
            Milestone("on_confirmation_page", weight=0.10,
                      check=lambda p: _on_url(p, "/order/")),
        ],
    )


# --------------------------------------------------------------------------- #
# Category M: cross-app journeys — read multiple app stores + the event log
# --------------------------------------------------------------------------- #

def _mail_inbox(probe: Probe) -> dict:
    if probe.world is None or getattr(probe.world, "mail", None) is None:
        return {}
    return probe.world.mail.inbox


def _mouse_order_id(probe: Probe) -> str | None:
    """Id of the shop order holding the STANDARD wireless mouse (and no mouse
    distractor). None if there is no such order."""
    distractors = {"p_mouse_gaming", "p_mouse_ergonomic",
                   "p_mouse_mini", "p_mouse_trackpad"}
    for o in probe.state.orders.values():
        pids = {it.product_id for it in o.items}
        if "p_mouse_wireless" in pids and not (pids & distractors):
            return o.id
    return None


def _suite_m2() -> TaskSuite:
    """NORTH-STAR. Order the standard wireless mouse -> open the order-
    confirmation email -> use its tracking link to view the package status
    for the RIGHT order. The cross-app memory hop (carry the order id from
    Mail back to the shop tracking page) is where weak agents break:
    confirmation_email_not_checked, order_id_memory_loss,
    wrong_source_of_truth, premature_finish_without_verification."""

    def _mouse_ordered(p: Probe) -> bool:
        return _mouse_order_id(p) is not None

    def _confirmation_delivered(p: Probe) -> bool:
        oid = _mouse_order_id(p)
        return oid is not None and any(
            e.order_id == oid for e in _mail_inbox(p).values()
        )

    def _confirmation_opened(p: Probe) -> bool:
        oid = _mouse_order_id(p)
        return oid is not None and any(
            e.order_id == oid and e.read for e in _mail_inbox(p).values()
        )

    def _tracking_viewed_correct(p: Probe) -> bool:
        oid = _mouse_order_id(p)
        return oid is not None and _log_has(p, "viewed_tracking", order_id=oid)

    return TaskSuite(
        task_id="M2/order_then_track_via_email",
        milestones=[
            Milestone("mouse_ordered", weight=0.30,
                      check=_mouse_ordered, required_for_success=True),
            Milestone("confirmation_email_delivered", weight=0.15,
                      check=_confirmation_delivered),
            Milestone("opened_confirmation_email", weight=0.25,
                      check=_confirmation_opened, required_for_success=True),
            Milestone("tracking_viewed_for_correct_order", weight=0.30,
                      check=_tracking_viewed_correct,
                      required_for_success=True),
        ],
    )


def _suite_m3() -> TaskSuite:
    """Order dinner from the Food app -> open the receipt email for THAT
    order. Spans Food -> Mail; the agent must open the RIGHT receipt, not an
    older inbox message."""

    def _food_order_ids(p: Probe) -> set[str]:
        if p.world is None or getattr(p.world, "food", None) is None:
            return set()
        return set(p.world.food.orders)

    def _food_order_placed(p: Probe) -> bool:
        return len(_food_order_ids(p)) > 0

    def _receipt_delivered(p: Probe) -> bool:
        oids = _food_order_ids(p)
        return any(e.order_id in oids for e in _mail_inbox(p).values())

    def _receipt_opened(p: Probe) -> bool:
        oids = _food_order_ids(p)
        return any(
            e.order_id in oids and e.read for e in _mail_inbox(p).values()
        )

    return TaskSuite(
        task_id="M3/dinner_then_receipt",
        milestones=[
            Milestone("food_order_placed", weight=0.40,
                      check=_food_order_placed, required_for_success=True),
            Milestone("receipt_email_delivered", weight=0.20,
                      check=_receipt_delivered),
            Milestone("opened_receipt_email", weight=0.40,
                      check=_receipt_opened, required_for_success=True),
        ],
    )


def _suite_m4() -> TaskSuite:
    """Difficulty lever. Order the mouse, then REPLY to the confirmation
    email with the exact CHARGED total (subtotal + tax + shipping). The value
    trap: the charged total != the sticker price, so an agent that doesn't
    actually open + read the email replies with the wrong number. Expected
    failures: replied_with_sticker_price_not_total, never_replied,
    confirmation_email_not_checked."""

    def _order_total(p: Probe) -> float | None:
        oid = _mouse_order_id(p)
        if oid is None:
            return None
        o = p.state.orders.get(oid)
        return o.total if o is not None else None

    def _mouse_ordered(p: Probe) -> bool:
        return _mouse_order_id(p) is not None

    def _confirmation_opened(p: Probe) -> bool:
        oid = _mouse_order_id(p)
        return oid is not None and any(
            e.order_id == oid and e.read for e in _mail_inbox(p).values()
        )

    def _sent_emails(p: Probe) -> list:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return []
        return list(p.world.mail.sent.values())

    def _replied_to_confirmation(p: Probe) -> bool:
        return any(
            ("orders@shopgym.com" in (e.to or "").lower()
             or (e.subject or "").lower().startswith("re:"))
            for e in _sent_emails(p)
        )

    def _reply_has_correct_total(p: Probe) -> bool:
        total = _order_total(p)
        if total is None:
            return False
        needle = f"{total:.2f}"          # the charged total, e.g. "27.68"
        return any(needle in (e.body or "") for e in _sent_emails(p))

    return TaskSuite(
        task_id="M4/order_then_reply_total",
        milestones=[
            Milestone("mouse_ordered", weight=0.25,
                      check=_mouse_ordered, required_for_success=True),
            Milestone("opened_confirmation_email", weight=0.20,
                      check=_confirmation_opened, required_for_success=True),
            Milestone("replied_to_confirmation", weight=0.20,
                      check=_replied_to_confirmation, required_for_success=True),
            Milestone("reply_states_correct_charged_total", weight=0.35,
                      check=_reply_has_correct_total,
                      required_for_success=True),
        ],
    )


def _suite_m5() -> TaskSuite:
    """Comparison + salience trap. Two 'deal' emails: the flashy one pushes
    the PRICIER gaming mouse ($20); the boring one has the cheaper ergonomic
    mouse ($16). Correct = read both, order the ergonomic. Expected failures:
    ordered_the_flashy_decoy (gaming), ordered_the_default_mouse (wireless),
    didn't_read_both_deals."""

    OTHER_MICE = ("p_mouse_gaming", "p_mouse_wireless",
                  "p_mouse_mini", "p_mouse_trackpad")

    def _both_deals_opened(p: Probe) -> bool:
        deals = [e for e in _mail_inbox(p).values()
                 if "mouse-deal" in (e.labels or [])]
        return len(deals) >= 2 and all(e.read for e in deals)

    def _ordered_cheaper(p: Probe) -> bool:
        # The ergonomic mouse is the genuinely-cheaper deal ($16 < $20).
        return _order_with(
            p, product_ids=("p_mouse_ergonomic",),
            exclude_product_ids=OTHER_MICE,
        )

    return TaskSuite(
        task_id="M5/cheaper_mouse_from_deals",
        milestones=[
            Milestone("both_deal_emails_opened", weight=0.30,
                      check=_both_deals_opened),
            Milestone("ordered_cheaper_ergonomic_mouse", weight=0.70,
                      check=_ordered_cheaper, required_for_success=True),
        ],
    )


def _suite_m6() -> TaskSuite:
    """Reorder the BIGGER past order's in-stock items, then reply listing
    them. Bigger order B = laptop + keyboard + charger (charger now OOS), so
    the correct reorder is laptop + keyboard. Pre-seeded order B itself is
    excluded by the charger; order A (mouse) is the wrong order. Expected
    failures: reordered_the_wrong_order, reordered_partial, never_replied,
    goal_incomplete_no_order."""

    def _reordered_correct(p: Probe) -> bool:
        # A NEW order holding exactly the bigger order's in-stock items
        # (laptop + keyboard), without the OOS charger or order A's mouse.
        return _order_with(
            p, product_ids=("p_laptop_studio", "p_kb_mech"),
            exclude_product_ids=("p_charger", "p_mouse_wireless"),
        )

    def _replied_with_item_list(p: Probe) -> bool:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return False
        for e in p.world.mail.sent.values():
            b = (e.body or "").lower()
            if "laptop" in b and "keyboard" in b:
                return True
        return False

    return TaskSuite(
        task_id="M6/reorder_bigger_order",
        milestones=[
            Milestone("reordered_bigger_orders_instock_items", weight=0.65,
                      check=_reordered_correct, required_for_success=True),
            Milestone("replied_listing_reordered_items", weight=0.35,
                      check=_replied_with_item_list, required_for_success=True),
        ],
    )


def _suite_m7() -> TaskSuite:
    """3-app: food order under $35 + a host gift that is a book rated >=4.5
    AND under $20 (only Project Hail Mary qualifies) + a reply to Alex
    carrying the food ETA AND the book name. Expected failures:
    over_budget_food, bought_disqualified_book, reply_missing_eta_or_book,
    never_replied."""

    QUALIFYING_BOOK = "p_book_sci_fi"
    DECOY_BOOKS = ("p_book_history", "p_book_cook", "p_book_oos",
                   "p_book_sci_fi_signed")

    def _food_under_budget(p: Probe) -> bool:
        if p.world is None or getattr(p.world, "food", None) is None:
            return False
        return any(o.total < 35.0 for o in p.world.food.orders.values())

    def _bought_qualifying_book(p: Probe) -> bool:
        for o in p.state.orders.values():
            for it in o.items:
                prod = p.state.products.get(it.product_id)
                if (it.product_id == QUALIFYING_BOOK and prod is not None
                        and prod.rating >= 4.5 and it.unit_price < 20.0):
                    return True
        return False

    def _avoided_decoy_books(p: Probe) -> bool:
        return not any(
            it.product_id in DECOY_BOOKS
            for o in p.state.orders.values() for it in o.items
        )

    def _replied_to_alex(p: Probe) -> bool:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return False
        etas = [o.eta_label for o in p.world.food.orders.values()] \
            if p.world.food is not None else []
        for e in p.world.mail.sent.values():
            to = (e.to or "").lower()
            body = (e.body or "").lower()
            if ("alex" in to and "hail mary" in body
                    and any(eta.lower() in body for eta in etas)):
                return True
        return False

    return TaskSuite(
        task_id="M7/dinner_and_host_gift",
        milestones=[
            Milestone("food_order_under_35", weight=0.30,
                      check=_food_under_budget, required_for_success=True),
            Milestone("bought_qualifying_book", weight=0.30,
                      check=_bought_qualifying_book, required_for_success=True),
            Milestone("avoided_disqualified_books", weight=0.10,
                      check=_avoided_decoy_books),
            Milestone("replied_to_alex_with_eta_and_book", weight=0.30,
                      check=_replied_to_alex, required_for_success=True),
        ],
    )


def _suite_m8() -> TaskSuite:
    """Aggregation + conditional branch + superlative. The three seeded
    shop orders total $1,319.92 (> $1,000), so the CORRECT branch is: buy
    nothing new and reply to the MOST EXPENSIVE order (ORD-P2) asking to
    cancel it. Expected failures: took_the_treat_yourself_branch (bought
    coffee / thanked), miscomputed_total -> wrong branch, replied_to_wrong
    _order, did_nothing."""

    MOST_EXPENSIVE = "ORD-P2"

    def _sent(p: Probe) -> list:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return []
        return list(p.world.mail.sent.values())

    def _replied_cancel_to_most_expensive(p: Probe) -> bool:
        for e in _sent(p):
            haystack = ((e.subject or "") + " " + (e.body or "")).upper()
            if MOST_EXPENSIVE in haystack and "cancel" in (e.body or "").lower():
                return True
        return False

    def _no_new_purchase(p: Probe) -> bool:
        # The correct branch buys NOTHING: only the 3 seeded shop orders
        # remain, and no food order was placed.
        shop_ok = len(p.state.orders) <= 3
        food_ok = True
        if p.world is not None and getattr(p.world, "food", None) is not None:
            food_ok = len(p.world.food.orders) == 0
        return shop_ok and food_ok

    return TaskSuite(
        task_id="M8/spending_audit_branch",
        milestones=[
            Milestone("replied_cancel_to_most_expensive_order", weight=0.60,
                      check=_replied_cancel_to_most_expensive,
                      required_for_success=True),
            Milestone("correct_branch_made_no_new_purchase", weight=0.40,
                      check=_no_new_purchase, required_for_success=True),
        ],
    )


def _suite_m9() -> TaskSuite:
    """4-app, free/busy-GATED branch. The correct branch flips with the seeded
    calendar (read from initial_world, the env truth):

      FREE evening -> order food + add a user calendar event + email Alex to
                      CONFIRM (not Thursday).
      BUSY evening -> do NOT order, do NOT add an event, email Alex to PROPOSE
                      THURSDAY.

    Each milestone scores the action that is correct FOR THE SEEDED BRANCH, so
    the classic trap (assume free, order anyway) fails the food + email
    milestones on busy seeds, and skipping the calendar read is no longer a
    free pass. Expected failures: ordered_despite_busy_calendar,
    proposed_thursday_when_free, forgot_calendar_event, forgot_food_order,
    wrong_or_missing_email."""
    from server.apps.calendar.state import evening_free as _evening_free

    def _free(p: Probe) -> bool:
        iw = p.initial_world
        return _evening_free(getattr(iw, "calendar", None) if iw else None)

    def _has_food_order(p: Probe) -> bool:
        return (p.world is not None
                and getattr(p.world, "food", None) is not None
                and len(p.world.food.orders) > 0)

    def _has_user_event(p: Probe) -> bool:
        if p.world is None or getattr(p.world, "calendar", None) is None:
            return False
        return any(e.source == "user"
                   for e in p.world.calendar.events.values())

    def _food_action_matches_branch(p: Probe) -> bool:
        # FREE -> a food order must exist; BUSY -> none should.
        return _has_food_order(p) if _free(p) else (not _has_food_order(p))

    def _calendar_action_matches_branch(p: Probe) -> bool:
        # FREE -> a user calendar event must exist; BUSY -> none should.
        return _has_user_event(p) if _free(p) else (not _has_user_event(p))

    def _emailed_alex_correct_branch(p: Probe) -> bool:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return False
        free = _free(p)
        for e in p.world.mail.sent.values():
            to = (e.to or "").lower()
            body = (e.body or "").lower()
            if "alex" not in to:
                continue
            if free:
                # CONFIRM branch — references dinner/tomorrow/confirm, and is
                # NOT the propose-Thursday branch.
                if ("thursday" not in body
                        and any(w in body for w in ("dinner", "tomorrow", "confirm"))):
                    return True
            else:
                # PROPOSE-THURSDAY branch.
                if "thursday" in body:
                    return True
        return False

    return TaskSuite(
        task_id="M9/calendar_gated_dinner",
        milestones=[
            Milestone("food_action_matches_calendar", weight=0.35,
                      check=_food_action_matches_branch,
                      required_for_success=True),
            Milestone("calendar_event_matches_branch", weight=0.30,
                      check=_calendar_action_matches_branch,
                      required_for_success=True),
            Milestone("emailed_alex_correct_branch", weight=0.35,
                      check=_emailed_alex_correct_branch,
                      required_for_success=True),
        ],
    )


def _suite_m10() -> TaskSuite:
    """SOURCE-OF-TRUTH CONFLICT (calendar vs. email). The calendar always
    shows tomorrow evening free, so the correct branch hinges entirely on
    Alex's email (read from initial_world.mail — the env truth):

      Alex AVAILABLE (benign email) -> order dinner + email Alex to CONFIRM.
      Alex UNAVAILABLE (conflict)   -> do NOT order; email Alex to RESCHEDULE
                                       (another day / Thursday).

    The trap is anchoring on the always-free calendar and ordering anyway.
    Each milestone scores the action correct FOR THE EMAIL, so the
    calendar-only agent fails both food + email on conflict seeds. Expected
    failures: ordered_despite_alex_unavailable, confirmed_despite_conflict,
    no_reschedule_reply."""

    def _alex_available(p: Probe) -> bool:
        # Read Alex's SEEDED email; "another day" appears only in the conflict
        # variant. Default to available if the mail store is missing.
        iw = p.initial_world
        mail = getattr(iw, "mail", None) if iw else None
        if mail is None:
            return True
        for e in mail.inbox.values():
            if "alex@" in (e.sender or "").lower():
                body = (e.body or "").lower()
                conflict = any(w in body for w in
                               ("another day", "can't make", "won't land",
                                "can't do dinner", "reschedule"))
                return not conflict
        return True

    def _has_food_order(p: Probe) -> bool:
        return (p.world is not None
                and getattr(p.world, "food", None) is not None
                and len(p.world.food.orders) > 0)

    def _food_action_matches_sources(p: Probe) -> bool:
        # AVAILABLE -> a food order must exist; UNAVAILABLE -> none should.
        return _has_food_order(p) if _alex_available(p) else (not _has_food_order(p))

    def _emailed_alex_correct_branch(p: Probe) -> bool:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return False
        available = _alex_available(p)
        reschedule_words = ("another day", "thursday", "reschedule",
                            "different day", "move", "another time",
                            "some other")
        for e in p.world.mail.sent.values():
            to = (e.to or "").lower()
            body = (e.body or "").lower()
            if "alex" not in to:
                continue
            proposed_resched = any(w in body for w in reschedule_words)
            if available:
                # CONFIRM branch — references dinner/tomorrow/confirm and does
                # NOT try to move the date.
                if (not proposed_resched
                        and any(w in body for w in ("confirm", "see you",
                                                    "tomorrow", "dinner"))):
                    return True
            else:
                # RESCHEDULE branch.
                if proposed_resched:
                    return True
        return False

    return TaskSuite(
        task_id="M10/dinner_source_conflict",
        milestones=[
            Milestone("food_action_matches_sources", weight=0.5,
                      check=_food_action_matches_sources,
                      required_for_success=True),
            Milestone("emailed_alex_correct_branch", weight=0.5,
                      check=_emailed_alex_correct_branch,
                      required_for_success=True),
        ],
    )


def _suite_m11() -> TaskSuite:
    """LONG-HORIZON RECONCILIATION over 8 confusable order emails. The agent
    must reply-cancel EXACTLY the orders that are over $100 AND not shipped.
    Ground truth (Q) is read from the SEEDED inbox; the agent's cancellations
    (C) are read from sent emails (subject/body names the order id + 'cancel').
    Success iff C == Q. Two precision milestones isolate the two failure
    directions: missed a qualifying cancel (lost track over many items) vs.
    cancelled a trap (shipped-but-expensive / cheap / just-under-$100)."""

    def _all_orders(p: Probe) -> dict[str, tuple[float, bool]]:
        iw = p.initial_world
        mail = getattr(iw, "mail", None) if iw else None
        out: dict[str, tuple[float, bool]] = {}
        if mail is None:
            return out
        for e in mail.inbox.values():
            oid = e.order_id or ""
            if not oid.startswith("ORD-"):
                continue
            shipped = "status: shipped" in (e.body or "").lower()
            out[oid] = (e.amount_total or 0.0, shipped)
        return out

    def _qualifying(p: Probe) -> set[str]:
        return {oid for oid, (tot, shipped) in _all_orders(p).items()
                if tot > 100.0 and not shipped}

    def _cancelled(p: Probe) -> set[str]:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return set()
        out: set[str] = set()
        for oid in _all_orders(p):
            for se in p.world.mail.sent.values():
                hay = ((se.subject or "") + " " + (se.body or ""))
                if oid in hay and "cancel" in (se.body or "").lower():
                    out.add(oid)
                    break
        return out

    def _cancelled_all_qualifying(p: Probe) -> bool:
        # Every order that SHOULD be cancelled was (no misses). Requires at
        # least one qualifying order to exist (it always does here).
        q = _qualifying(p)
        return bool(q) and q.issubset(_cancelled(p))

    def _cancelled_only_qualifying(p: Probe) -> bool:
        # NOTHING that shouldn't be cancelled was (no traps hit, no extras).
        return _cancelled(p).issubset(_qualifying(p))

    return TaskSuite(
        task_id="M11/cancel_unshipped_over_100",
        milestones=[
            Milestone("cancelled_all_qualifying", weight=0.5,
                      check=_cancelled_all_qualifying,
                      required_for_success=True),
            Milestone("cancelled_only_qualifying", weight=0.5,
                      check=_cancelled_only_qualifying,
                      required_for_success=True),
        ],
    )


def _suite_m12() -> TaskSuite:
    """BUTTON-DENSITY / SMALL-TARGET stress. The dense Quick Order grid has a
    generic 'Add' button per item; the agent must add EXACTLY the mice +
    keyboards and nothing else. Cart must equal the qualifying set. Two
    precision milestones split the failure directions: missed a qualifying add
    (skipped one in the crowd) vs. added a non-qualifying item (mis-mapped a
    crowded Add button to the wrong product -- the predicted small-target
    mis-click)."""

    def _qualifying(p: Probe) -> set[str]:
        return {pid for pid, pr in p.state.products.items()
                if "mouse" in pr.name.lower() or "keyboard" in pr.name.lower()}

    def _cart(p: Probe) -> set[str]:
        return {it.product_id for it in p.state.cart.items}

    def _added_all_qualifying(p: Probe) -> bool:
        q = _qualifying(p)
        return bool(q) and q.issubset(_cart(p))

    def _added_only_qualifying(p: Probe) -> bool:
        c = _cart(p)
        return bool(c) and c.issubset(_qualifying(p))

    return TaskSuite(
        task_id="M12/bulk_add_dense_grid",
        milestones=[
            Milestone("added_all_qualifying", weight=0.5,
                      check=_added_all_qualifying, required_for_success=True),
            Milestone("added_only_qualifying", weight=0.5,
                      check=_added_only_qualifying, required_for_success=True),
        ],
    )


def _suite_m13() -> TaskSuite:
    """CONJUNCTIVE BOUNDARY-TRAP reconciliation. Cancel exactly the orders that
    are UNSHIPPED AND CHARGED > $50 (amount_total = charged) AND NOT the gift.
    Ground truth (Q) is read from the seeded inbox; cancellations (C) from sent
    emails. Success iff C == Q over 14 items. Two precision milestones split
    the failure directions, and the harvester pins the cause (read subtotal
    instead of charged / cancelled the gift / missed one)."""

    def _all_orders(p: Probe) -> dict[str, tuple[float, bool, bool]]:
        # oid -> (charged, shipped, is_gift)
        iw = p.initial_world
        mail = getattr(iw, "mail", None) if iw else None
        out: dict[str, tuple[float, bool, bool]] = {}
        if mail is None:
            return out
        for e in mail.inbox.values():
            oid = e.order_id or ""
            if not oid.startswith("ORD-"):
                continue
            body = (e.body or "").lower()
            shipped = "status: shipped" in body
            is_gift = "gift note" in body
            out[oid] = (e.amount_total or 0.0, shipped, is_gift)
        return out

    def _qualifying(p: Probe) -> set[str]:
        return {oid for oid, (chg, shipped, gift) in _all_orders(p).items()
                if chg > 50.0 and not shipped and not gift}

    def _cancelled(p: Probe) -> set[str]:
        if p.world is None or getattr(p.world, "mail", None) is None:
            return set()
        out: set[str] = set()
        for oid in _all_orders(p):
            for se in p.world.mail.sent.values():
                hay = (se.subject or "") + " " + (se.body or "")
                if oid in hay and "cancel" in (se.body or "").lower():
                    out.add(oid)
                    break
        return out

    def _cancelled_all_required(p: Probe) -> bool:
        q = _qualifying(p)
        return bool(q) and q.issubset(_cancelled(p))

    def _cancelled_only_required(p: Probe) -> bool:
        # No skips cancelled: not a charged<=$50 trap, not shipped, not the gift.
        return _cancelled(p).issubset(_qualifying(p))

    return TaskSuite(
        task_id="M13/order_cleanup_audit",
        milestones=[
            Milestone("cancelled_all_required", weight=0.5,
                      check=_cancelled_all_required, required_for_success=True),
            Milestone("cancelled_only_required", weight=0.5,
                      check=_cancelled_only_required, required_for_success=True),
        ],
    )


def _suite_m14() -> TaskSuite:
    """ASYNC return -> refund. File the return for the mouse only; a
    RefundApproved email arrives 3 steps later (scheduler) with the exact
    refund; reply confirming that exact amount. The 4 levels:
      delivered  -> refund_email_delivered (env truth, bus.has_delivered)
      read       -> opened_refund_email (the agent NOTICED the async arrival)
      used       -> replied_confirming_refund (exact amount in the reply)
    plus the return itself. refund_email_delivered is weight 0 (an env-truth
    gate for the async-recovery metric, not scored)."""
    from server.apps import bus as _bus
    import re as _re

    def _support_rma(p: Probe):
        """The RMA code from the seeded support email (env truth)."""
        mail = getattr(p.initial_world, "mail", None) if p.initial_world else None
        if mail is None:
            return None
        for e in mail.inbox.values():
            if "support@" in (e.sender or "").lower():
                m = _re.search(r"RMA-\d+", e.body or "")
                return m.group(0) if m else None
        return None

    def _return_mouse_only(p: Probe) -> bool:
        return any(r.order_id == "ORD-RET-1" and r.item_ids == ["ln_mouse"]
                   and r.refund_method == "original_payment"
                   for r in p.state.returns.values())

    def _return_quotes_rma(p: Probe) -> bool:
        """The agent carried the RMA from the support email INTO the return's
        notes (the cross-tab transfer IN)."""
        rma = _support_rma(p)
        if not rma:
            return False
        return any(r.order_id == "ORD-RET-1" and rma in (r.notes or "")
                   for r in p.state.returns.values())

    def _refund_delivered(p: Probe) -> bool:
        return p.world is not None and _bus.has_delivered(p.world, "RefundApproved")

    def _refund_email(p: Probe):
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return None
        for e in mail.inbox.values():
            if "refunds@" in (e.sender or "").lower():
                return e
        return None

    def _opened_refund_email(p: Probe) -> bool:
        e = _refund_email(p)
        return e is not None and e.read

    def _replied_confirming_refund(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        e = _refund_email(p)
        if mail is None or e is None or e.amount_total is None:
            return False
        needle = f"{e.amount_total:.2f}"           # the EXACT refund amount
        for se in mail.sent.values():
            body = se.body or ""
            to = (se.to or "").lower()
            if needle in body and "refund" in to:
                return True
        return False

    return TaskSuite(
        task_id="M14/return_then_refund",
        milestones=[
            Milestone("return_filed_mouse_only", weight=0.25,
                      check=_return_mouse_only, required_for_success=True),
            Milestone("return_quotes_rma", weight=0.15,
                      check=_return_quotes_rma, required_for_success=True),
            Milestone("refund_email_delivered", weight=0.0,
                      check=_refund_delivered, required_for_success=False),
            Milestone("opened_refund_email", weight=0.2,
                      check=_opened_refund_email, required_for_success=True),
            Milestone("replied_confirming_refund", weight=0.4,
                      check=_replied_confirming_refund,
                      required_for_success=True),
        ],
    )


def _suite_m15() -> TaskSuite:
    """ASYNC price-watch + stale-state. A PriceDropAlert email lands at step 4
    naming ONE mouse + a new price; its pair drops that mouse's price in the
    shop. Buy exactly that mouse at the NEW price. The 4 levels:
      delivered -> alert_delivered (env truth, bus.has_delivered) [weight 0]
      (shop)    -> price_dropped_in_shop (the paired mutation fired) [weight 0]
      read      -> opened_alert_email (the agent noticed the async arrival)
      used      -> ordered_correct_mouse_only + ordered_at_dropped_price
    An agent that buys before step 4 gets the stale (old) unit price and fails
    ordered_at_dropped_price; one that buys the wrong mouse fails
    ordered_correct_mouse_only."""
    from server.apps import bus as _bus

    _ALL_MICE = {"p_mouse_wireless", "p_mouse_gaming", "p_mouse_ergonomic",
                 "p_mouse_mini", "p_mouse_trackpad"}

    def _alert_email(p: Probe):
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return None
        for e in mail.inbox.values():
            if "price-drop" in (e.labels or []) \
                    or "alerts@" in (e.sender or "").lower():
                return e
        return None

    def _alerted_pid(p: Probe):
        e = _alert_email(p)
        return e.product_id if e is not None else None

    def _alerted_price(p: Probe):
        e = _alert_email(p)
        return e.amount_total if e is not None else None

    def _alert_delivered(p: Probe) -> bool:
        return p.world is not None and _bus.has_delivered(p.world, "PriceDropAlert")

    def _price_dropped_in_shop(p: Probe) -> bool:
        pid = _alerted_pid(p)
        price = _alerted_price(p)
        if not pid or price is None:
            return False
        prod = p.state.products.get(pid)
        return prod is not None and abs(prod.base_price - price) < 0.01

    def _opened_alert_email(p: Probe) -> bool:
        e = _alert_email(p)
        return e is not None and e.read

    def _ordered_correct_mouse_only(p: Probe) -> bool:
        """An order contains the alerted mouse AND no OTHER mouse (resists
        buying the wrong/extra mouse)."""
        pid = _alerted_pid(p)
        if not pid:
            return False
        others = _ALL_MICE - {pid}
        found = False
        for o in p.state.orders.values():
            pids = {it.product_id for it in o.items}
            if pids & others:
                return False
            if pid in pids:
                found = True
        return found

    def _ordered_at_dropped_price(p: Probe) -> bool:
        """The alerted mouse's order line carries the NEW price — not the stale
        pre-drop price an early buyer would have locked in."""
        pid = _alerted_pid(p)
        price = _alerted_price(p)
        if not pid or price is None:
            return False
        for o in p.state.orders.values():
            for it in o.items:
                if it.product_id == pid:
                    return abs(it.unit_price - price) < 0.01
        return False

    return TaskSuite(
        task_id="M15/inbox_price_watch",
        milestones=[
            Milestone("alert_delivered", weight=0.0,
                      check=_alert_delivered, required_for_success=False),
            Milestone("price_dropped_in_shop", weight=0.0,
                      check=_price_dropped_in_shop, required_for_success=False),
            # INFORMATIONAL (not required, weight 0): the alert's subject line
            # already names the mouse + new price, so an agent can do the real
            # task by reading the inbox list without OPENING the email. We grade
            # the OUTCOME (right mouse at the new price), not whether the email
            # was opened — opening is recorded for the coverage metric only.
            Milestone("opened_alert_email", weight=0.0,
                      check=_opened_alert_email, required_for_success=False),
            Milestone("ordered_correct_mouse_only", weight=0.5,
                      check=_ordered_correct_mouse_only,
                      required_for_success=True),
            Milestone("ordered_at_dropped_price", weight=0.5,
                      check=_ordered_at_dropped_price,
                      required_for_success=True),
        ],
    )


def _suite_m16() -> TaskSuite:
    """HERO async branch-flip + NEGATIVE action. Order dinner, reminder + guest
    note at the first ETA; a DeliveryDelayed notice then pushes the ETA later,
    so the agent must move the reminder to the new ETA (leaving exactly ONE
    delivery event) AND tell the guest the new time. The 4 levels:
      delivered -> delivery_delayed_delivered (env truth) [weight 0]
      read      -> noticed_delay (opened the delay notice)
      used      -> calendar_reflects_new_eta_only (the negative action: one
                   user event, at the new 20:00 — not two, not the stale 19:00)
                   + emailed_guest_new_eta (told the guest the new time)
    food_order_placed is a required weight-0 gate (no order -> nothing to
    coordinate)."""
    from server.apps import bus as _bus

    _NEW_24H = "20:00"
    _NEW_TOKENS = ("8:00", "8 pm", "8pm", "20:00")

    def _food_ordered(p: Probe) -> bool:
        food = getattr(p.world, "food", None) if p.world else None
        return food is not None and len(food.orders) >= 1

    def _delay_delivered(p: Probe) -> bool:
        return p.world is not None and _bus.has_delivered(p.world, "DeliveryDelayed")

    def _delay_email(p: Probe):
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return None
        for e in mail.inbox.values():
            if "delivery" in (e.labels or []) \
                    or "delivery@" in (e.sender or "").lower():
                return e
        return None

    def _noticed_delay(p: Probe) -> bool:
        e = _delay_email(p)
        return e is not None and e.read

    def _user_events(p: Probe) -> list:
        cal = getattr(p.world, "calendar", None) if p.world else None
        if cal is None:
            return []
        return [e for e in cal.events.values() if e.source == "user"]

    def _calendar_reflects_new_eta_only(p: Probe) -> bool:
        """Exactly ONE agent-created event, at the NEW ETA. Catches both the
        over-keep (two events) and the never-updated (one event still at the
        old 19:00) failures."""
        evs = _user_events(p)
        return len(evs) == 1 and evs[0].start == _NEW_24H

    def _emailed_guest_new_eta(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        for se in mail.sent.values():
            to = (se.to or "").lower()
            body = (se.body or "").lower()
            if "alex" in to and any(t in body for t in _NEW_TOKENS):
                return True
        return False

    return TaskSuite(
        task_id="M16/coordinated_dinner_delay",
        milestones=[
            Milestone("food_order_placed", weight=0.0,
                      check=_food_ordered, required_for_success=True),
            Milestone("delivery_delayed_delivered", weight=0.0,
                      check=_delay_delivered, required_for_success=False),
            Milestone("noticed_delay", weight=0.2,
                      check=_noticed_delay, required_for_success=True),
            Milestone("calendar_reflects_new_eta_only", weight=0.4,
                      check=_calendar_reflects_new_eta_only,
                      required_for_success=True),
            Milestone("emailed_guest_new_eta", weight=0.4,
                      check=_emailed_guest_new_eta, required_for_success=True),
        ],
    )


def _suite_m20() -> TaskSuite:
    """BUNDLED ERRAND RUN — four independent sub-goals across 5 apps, ALL
    required (so dropping any one fails the task; the missed milestone shows
    which). Positive end-state checks:
      gear     -> ordered_gear_valuemart (keyboard+mouse on ValueMart w/ VALUE10,
                  under $125)
      dinner   -> dinner_ordered (a Sakura Sushi food order)
      calendar -> calendar_reminder_created (an agent-created calendar event)
      reply    -> replied_gear_total_to_alex (a sent email to Alex containing the
                  EXACT total of the gear order — the Shop->Mail value transfer)."""
    _GEAR = {"vm_kb_mech", "vm_mouse_wireless"}
    _BUDGET = 125.0

    def _gear_orders(p: Probe) -> list:
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return []
        return [o for o in mk.orders.values()
                if _GEAR.issubset({it.product_id for it in o.items})]

    def _ordered_gear(p: Probe) -> bool:
        return any(o.coupon_code == "VALUE10" and o.total <= _BUDGET
                   for o in _gear_orders(p))

    def _dinner_ordered(p: Probe) -> bool:
        food = getattr(p.world, "food", None) if p.world else None
        if food is None:
            return False
        return any(o.restaurant_id == "r_sushi" for o in food.orders.values())

    def _calendar_reminder(p: Probe) -> bool:
        cal = getattr(p.world, "calendar", None) if p.world else None
        if cal is None:
            return False
        return any(e.source == "user" for e in cal.events.values())

    def _replied_gear_total_to_alex(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        orders = _gear_orders(p)
        if mail is None or not orders:
            return False
        needle = f"{orders[0].total:.2f}"            # the EXACT charged total
        return any("alex" in (se.to or "").lower() and needle in (se.body or "")
                   for se in mail.sent.values())

    return TaskSuite(
        task_id="M20/errand_run",
        milestones=[
            Milestone("ordered_gear_valuemart", weight=0.3,
                      check=_ordered_gear, required_for_success=True),
            Milestone("dinner_ordered", weight=0.2,
                      check=_dinner_ordered, required_for_success=True),
            Milestone("calendar_reminder_created", weight=0.2,
                      check=_calendar_reminder, required_for_success=True),
            Milestone("replied_gear_total_to_alex", weight=0.3,
                      check=_replied_gear_total_to_alex,
                      required_for_success=True),
        ],
    )


def _suite_m21() -> TaskSuite:
    """ASYNC ERRAND RUN — M20's four-sub-goal juggle where an async flash-sale
    coupon (VALUEMART20, arrives step 4) makes the exact gear total a MOVING
    TARGET. All four sub-goals are required positive end-state checks, so the
    missed milestone pinpoints the drop:
      env gate -> flip_delivered (the async flash-sale email fired)
      caught   -> ordered_gear_with_flip_coupon (gear on ValueMart with the
                  POST-FLIP coupon VALUEMART20 — proves it noticed + applied the
                  mid-task flip, not the stale VALUE10)
      dinner   -> dinner_ordered (a Sakura Sushi order)
      calendar -> calendar_reminder_created (an agent-created calendar event)
      fresh    -> replied_postflip_total_to_alex (reply to Alex contains the
                  EXACT post-flip total $107.98 — a STALE $121.48 fails, catching
                  value-went-out-of-date-under-load)."""
    _GEAR = {"vm_kb_mech", "vm_mouse_wireless"}
    _FLIP = "VALUEMART20"

    def _flip_orders(p: Probe) -> list:
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return []
        return [o for o in mk.orders.values()
                if _GEAR.issubset({it.product_id for it in o.items})
                and o.coupon_code == _FLIP]

    def _ordered_gear_flip(p: Probe) -> bool:
        return len(_flip_orders(p)) >= 1

    def _dinner_ordered(p: Probe) -> bool:
        food = getattr(p.world, "food", None) if p.world else None
        if food is None:
            return False
        return any(o.restaurant_id == "r_sushi" for o in food.orders.values())

    def _calendar_reminder(p: Probe) -> bool:
        cal = getattr(p.world, "calendar", None) if p.world else None
        if cal is None:
            return False
        return any(e.source == "user" for e in cal.events.values())

    def _replied_postflip_total(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        orders = _flip_orders(p)
        if mail is None or not orders:
            return False
        needle = f"{orders[0].total:.2f}"        # the EXACT post-flip total
        return any("alex" in (se.to or "").lower() and needle in (se.body or "")
                   for se in mail.sent.values())

    def _flip_delivered(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        return any("coupon-flip" in (e.labels or [])
                   for e in mail.inbox.values())

    return TaskSuite(
        task_id="M21/async_errand_run",
        milestones=[
            Milestone("flip_delivered", weight=0.0,
                      check=_flip_delivered, required_for_success=False),
            Milestone("ordered_gear_with_flip_coupon", weight=0.3,
                      check=_ordered_gear_flip, required_for_success=True),
            Milestone("dinner_ordered", weight=0.2,
                      check=_dinner_ordered, required_for_success=True),
            Milestone("calendar_reminder_created", weight=0.2,
                      check=_calendar_reminder, required_for_success=True),
            Milestone("replied_postflip_total_to_alex", weight=0.3,
                      check=_replied_postflip_total, required_for_success=True),
        ],
    )


def _suite_m22() -> TaskSuite:
    """ASYNC CALENDAR CASCADE — destructive overwrite + ripple under juggling
    load. All four sub-goals are required POSITIVE end-state checks (no sticky
    negatives), so the missed milestone pinpoints the drop:
      env gate -> change_alert_delivered (the async manager email fired)
      juggle   -> coffee_ordered (a Bean There Cafe order — concurrent load)
      move     -> oneonone_moved_to_2pm (EXACTLY one 1:1-with-Priya event, now
                  at 14:00 — catches duplicate/forgot-to-move)
      DELETE   -> cancelled_sync_deleted (no 'Team Sync' event remains — the
                  destructive action agents skip, leaving a 2 PM double-booking)
      notify   -> notified_priya_new_time (a sent email to Priya carrying the
                  new 2 PM time — the cross-app value ripple)."""

    def _events(p: Probe) -> list:
        cal = getattr(p.world, "calendar", None) if p.world else None
        return list(cal.events.values()) if cal is not None else []

    def _coffee_ordered(p: Probe) -> bool:
        food = getattr(p.world, "food", None) if p.world else None
        if food is None:
            return False
        return any(o.restaurant_id == "r_bean" for o in food.orders.values())

    def _oneonone_moved(p: Probe) -> bool:
        priya = [e for e in _events(p) if "priya" in (e.title or "").lower()]
        return len(priya) == 1 and priya[0].start == "14:00"

    def _sync_deleted(p: Probe) -> bool:
        # False while the seeded Team Sync still exists; becomes True only once
        # the agent deletes it (so it is a positive 'deletion happened' check,
        # not a vacuous step-0 negative).
        return not any("team sync" in (e.title or "").lower()
                       for e in _events(p))

    def _notified_priya(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        needles = ("2:00", "2 pm", "2pm", "14:00")
        return any("priya" in (se.to or "").lower()
                   and any(n in (se.body or "").lower() for n in needles)
                   for se in mail.sent.values())

    def _change_delivered(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        return any("calendar-change" in (e.labels or [])
                   for e in mail.inbox.values())

    return TaskSuite(
        task_id="M22/async_calendar_cascade",
        milestones=[
            Milestone("change_alert_delivered", weight=0.0,
                      check=_change_delivered, required_for_success=False),
            Milestone("coffee_ordered", weight=0.2,
                      check=_coffee_ordered, required_for_success=True),
            Milestone("oneonone_moved_to_2pm", weight=0.3,
                      check=_oneonone_moved, required_for_success=True),
            Milestone("cancelled_sync_deleted", weight=0.3,
                      check=_sync_deleted, required_for_success=True),
            Milestone("notified_priya_new_time", weight=0.2,
                      check=_notified_priya, required_for_success=True),
        ],
    )


def _suite_m23() -> TaskSuite:
    """THE OFFSITE THAT KEEPS MOVING — derive + conflict + cascade + recipient.
    Four required POSITIVE end-state milestones (conjunctive), the missed one
    pinpoints the blocker that broke the agent:
      env gate -> swap_alert_delivered (the async attendee-swap email fired)
      DERIVE   -> lunch_veg_under_budget (a Burger Barn order that includes the
                  Veggie Burger AND totals < $40 — combines Priya's diet + Alex's
                  budget; resisting the salient Classic Cheeseburger default)
      CONFLICT+CASCADE -> meeting_after_3pm_free (a user calendar event starting
                  at EXACTLY 16:00 — the unique free after-3 PM slot once Dana's
                  constraint lands; catches not-moved-from-1 PM, the form's 19:00
                  default which is now a busy slot, and any other wrong time)
      RECIPIENT-> notified_dana (a sent email to dana@ with the final 4 PM time —
                  a FRESH compose, since Dana is not in the inbox; replying to the
                  manager misroutes)
      MULTI    -> notified_attendees (sent emails to BOTH Priya and Alex with the
                  final time)."""
    _TIME = ("4:00", "16:00", "4 pm", "4pm", "4 p.m")

    def _food_orders(p: Probe) -> list:
        food = getattr(p.world, "food", None) if p.world else None
        return list(food.orders.values()) if food is not None else []

    def _lunch_ok(p: Probe) -> bool:
        for o in _food_orders(p):
            if o.restaurant_id != "r_burger":
                continue
            has_veggie = any(it.dish_id == "d_veggie" for it in o.items)
            if has_veggie and o.total < 40.0:
                return True
        return False

    def _after_3pm_free(p: Probe) -> bool:
        cal = getattr(p.world, "calendar", None) if p.world else None
        if cal is None:
            return False
        # The calendar is busy 15:00-16:00 and 17:00-22:00, so the UNIQUE free
        # slot after 3 PM is 16:00-17:00. The lunch must start at exactly 16:00
        # (4 PM) — this rejects the new-event form's 19:00 default (a busy slot)
        # and any other time, and makes the 4 PM notify time unambiguous.
        return any(e.source == "user" and (e.start or "") == "16:00"
                   for e in cal.events.values())

    def _sent_with_time_to(p: Probe, who: str) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        return any(who in (se.to or "").lower()
                   and any(t in (se.body or "").lower() for t in _TIME)
                   for se in mail.sent.values())

    def _notified_dana(p: Probe) -> bool:
        return _sent_with_time_to(p, "dana")

    def _notified_attendees(p: Probe) -> bool:
        return _sent_with_time_to(p, "priya") and _sent_with_time_to(p, "alex")

    def _swap_delivered(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        return any("offsite-change" in (e.labels or [])
                   for e in mail.inbox.values())

    return TaskSuite(
        task_id="M23/offsite_keeps_moving",
        milestones=[
            Milestone("swap_alert_delivered", weight=0.0,
                      check=_swap_delivered, required_for_success=False),
            Milestone("lunch_veg_under_budget", weight=0.25,
                      check=_lunch_ok, required_for_success=True),
            Milestone("meeting_after_3pm_free", weight=0.25,
                      check=_after_3pm_free, required_for_success=True),
            Milestone("notified_dana", weight=0.25,
                      check=_notified_dana, required_for_success=True),
            Milestone("notified_attendees", weight=0.25,
                      check=_notified_attendees, required_for_success=True),
        ],
    )


def _suite_m24() -> TaskSuite:
    """PROCUREMENT PUZZLE — global-optimum trap. The only under-$320 path is
    consolidating the exact three items at ValueMart with VALUE10 (greedy
    per-item-cheapest splits stores and busts the budget). Three decoupled,
    POSITIVE end-state milestones:
      items  -> ordered_three_at_valuemart (one ValueMart order whose item set is
                EXACTLY {Wireless Mouse, Mechanical Keyboard, 24-inch Monitor} —
                rejects decoys/lookalikes, extras, and store-splitting)
      coupon -> applied_value10 (that order used the 10% code)
      budget -> under_budget (that order total <= $320 — only the consolidated
                optimum fits)."""
    _ITEMS = {"vm_mouse_wireless", "vm_kb_mech", "vm_monitor_24"}
    _BUDGET = 320.0

    def _target_orders(p: Probe) -> list:
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return []
        return [o for o in mk.orders.values()
                if {it.product_id for it in o.items} == _ITEMS]

    def _ordered_three(p: Probe) -> bool:
        return len(_target_orders(p)) >= 1

    def _applied_value10(p: Probe) -> bool:
        return any(o.coupon_code == "VALUE10" for o in _target_orders(p))

    def _under_budget(p: Probe) -> bool:
        return any(o.total <= _BUDGET for o in _target_orders(p))

    return TaskSuite(
        task_id="M24/procurement_puzzle",
        milestones=[
            Milestone("ordered_three_at_valuemart", weight=0.4,
                      check=_ordered_three, required_for_success=True),
            Milestone("applied_value10", weight=0.3,
                      check=_applied_value10, required_for_success=True),
            Milestone("under_budget", weight=0.3,
                      check=_under_budget, required_for_success=True),
        ],
    )


def _suite_m25() -> TaskSuite:
    """DISPATCH DESK — route each teammate's detail to the RIGHT person (scales
    the M22 reply-to-trigger / wrong-recipient failure to four channels), with a
    moving target on Alex (corrected $12,000 -> $21,000). Four decoupled POSITIVE
    per-person milestones: each requires a SENT email whose recipient is that
    person AND whose body carries THAT person's correct detail. Cross-wiring
    (Alex's figure to Priya), replying to the manager (neither person is the
    recipient), a stale Alex budget, or a dropped person each misses cleanly."""

    def _sent_to_with(p: Probe, who: str, needles) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        return any(who in (se.to or "").lower()
                   and any(n in (se.body or "").lower() for n in needles)
                   for se in mail.sent.values())

    def _priya(p: Probe) -> bool:
        return _sent_to_with(p, "priya", ("4:00", "4 pm", "4pm", "4 p.m"))

    def _alex(p: Probe) -> bool:                  # the CORRECTED budget, not 12k
        return _sent_to_with(p, "alex", ("21,000", "21000", "$21,000", "21k"))

    def _sam(p: Probe) -> bool:
        return _sent_to_with(p, "sam", ("friday",))

    def _dana(p: Probe) -> bool:
        return _sent_to_with(p, "dana", ("b12", "b-12", "b 12"))

    def _correction_delivered(p: Probe) -> bool:
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return False
        return any("dispatch-correction" in (e.labels or [])
                   for e in mail.inbox.values())

    return TaskSuite(
        task_id="M25/dispatch_desk",
        milestones=[
            Milestone("correction_delivered", weight=0.0,
                      check=_correction_delivered, required_for_success=False),
            Milestone("notified_priya_time", weight=0.25,
                      check=_priya, required_for_success=True),
            Milestone("notified_alex_budget", weight=0.25,
                      check=_alex, required_for_success=True),
            Milestone("notified_sam_deadline", weight=0.25,
                      check=_sam, required_for_success=True),
            Milestone("notified_dana_desk", weight=0.25,
                      check=_dana, required_for_success=True),
        ],
    )


def _suite_m26() -> TaskSuite:
    """ASYNC DESTRUCTIVE EXACT-SET PURGE. An async manager email (step 5) cancels
    Project Phoenix and instructs the agent to delete every Phoenix meeting EXCEPT
    the repurposed 'Phoenix Retro' (KEEP it). Success = the set of calendar events
    actually removed equals the target Q = {Phoenix meetings} - {Phoenix Retro}.

    Why set-equality is the right grader AND stickiness-safe: deletions only grow
    (the UI cannot un-delete; a re-created event gets a fresh id). So `deleted`
    climbs monotonically from {} and `deleted == Q` is False at the seed; it can
    only become True for the EXACT target. The instant the agent removes any
    non-target event (the kept Retro, an Atlas decoy, the 1:1), `deleted` is a
    strict superset of Q forever, so the exact-set milestone can never fire —
    catching over-deletion, which a sticky `deleted ⊆ Q` precision check could
    not (that is True at step 0). Two milestones split the failure direction:
      deleted_all_target    -> completeness (every Phoenix-to-go was removed)
      deleted_exactly_target-> precision    (and nothing else was removed)
    Weight-0 gates expose the async delivery + read + the engineered over-delete."""
    from server.apps import bus as _bus

    def _seed_titles(p: Probe) -> dict[str, str]:
        """event_id -> lowercased title, from the INITIAL (seed) calendar."""
        iw = p.initial_world
        cal = getattr(iw, "calendar", None) if iw else None
        if cal is None:
            return {}
        return {eid: (ev.title or "").lower() for eid, ev in cal.events.items()}

    def _target(p: Probe) -> set[str]:
        # Q = Phoenix meetings to delete = 'phoenix' in title AND NOT 'retro'
        # (the Retro is the repurposed exception the email says to KEEP). This
        # rule is kept in lockstep with the email body in mail/inbound.py.
        return {eid for eid, t in _seed_titles(p).items()
                if "phoenix" in t and "retro" not in t}

    def _exception(p: Probe) -> set[str]:
        return {eid for eid, t in _seed_titles(p).items()
                if "phoenix" in t and "retro" in t}

    def _deleted(p: Probe) -> set[str]:
        cur = getattr(getattr(p.world, "calendar", None), "events", {}) or {}
        return {eid for eid in _seed_titles(p) if eid not in cur}

    def _cancel_email(p: Probe):
        mail = getattr(p.world, "mail", None) if p.world else None
        if mail is None:
            return None
        for e in mail.inbox.values():
            if "project-cancelled" in (e.labels or []):
                return e
        return None

    def _delivered(p: Probe) -> bool:
        return p.world is not None and _bus.has_delivered(p.world, "ProjectCancelled")

    def _read(p: Probe) -> bool:
        e = _cancel_email(p)
        return e is not None and e.read

    def _deleted_all_target(p: Probe) -> bool:
        q = _target(p)
        return bool(q) and q.issubset(_deleted(p))

    def _deleted_exactly_target(p: Probe) -> bool:
        q = _target(p)
        return bool(q) and _deleted(p) == q

    def _over_deleted_exception(p: Probe) -> bool:
        exc = _exception(p)
        return bool(exc) and exc.issubset(_deleted(p))

    return TaskSuite(
        task_id="M26/calendar_purge_async",
        milestones=[
            Milestone("cancellation_email_delivered", weight=0.0,
                      check=_delivered, required_for_success=False),
            Milestone("read_cancellation_email", weight=0.0,
                      check=_read, required_for_success=False),
            Milestone("deleted_all_target", weight=0.5,
                      check=_deleted_all_target, required_for_success=True),
            Milestone("deleted_exactly_target", weight=0.5,
                      check=_deleted_exactly_target, required_for_success=True),
            Milestone("over_deleted_exception", weight=0.0,
                      check=_over_deleted_exception, required_for_success=False),
        ],
    )


def _suite_m19() -> TaskSuite:
    """COUPON MINEFIELD. Buy keyboard + mouse on the cheaper store (ValueMart)
    with the VALID coupon (VALUE10), under a $125 budget — resisting the salient
    but EXPIRED VALUEMART50. Positive end-state checks:
      env gate -> valuemart50_is_expired (the decoy really is expired)
      used     -> ordered_keyboard_and_mouse_valuemart + applied_value10
                  (rejected the expired 50%, used the valid 10%) + under_budget
                  (the coupon is load-bearing: no-coupon ValueMart busts $125)."""
    _GEAR = {"vm_kb_mech", "vm_mouse_wireless"}
    _BUDGET = 125.0

    def _vm_gear_orders(p: Probe) -> list:
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return []
        return [o for o in mk.orders.values()
                if _GEAR.issubset({it.product_id for it in o.items})]

    def _ordered_kb_mouse_vm(p: Probe) -> bool:
        return len(_vm_gear_orders(p)) >= 1

    def _applied_value10(p: Probe) -> bool:
        return any(o.coupon_code == "VALUE10" for o in _vm_gear_orders(p))

    def _under_budget(p: Probe) -> bool:
        return any(o.total <= _BUDGET for o in _vm_gear_orders(p))

    def _vm50_expired(p: Probe) -> bool:
        mk = getattr(p.world, "market", None) if p.world else None
        c = mk.coupons.get("VALUEMART50") if mk else None
        return c is not None and c.expired

    return TaskSuite(
        task_id="M19/coupon_minefield",
        milestones=[
            Milestone("valuemart50_is_expired", weight=0.0,
                      check=_vm50_expired, required_for_success=False),
            Milestone("ordered_keyboard_and_mouse_valuemart", weight=0.4,
                      check=_ordered_kb_mouse_vm, required_for_success=True),
            Milestone("applied_value10", weight=0.3,
                      check=_applied_value10, required_for_success=True),
            Milestone("under_budget", weight=0.3,
                      check=_under_budget, required_for_success=True),
        ],
    )


def _suite_m18() -> TaskSuite:
    """ASYNC COUPON-FLIP. Initially ShopGym (TECH20) is cheaper; an async
    FLASH-SALE email then announces VALUEMART30 (30%), making ValueMart the
    cheapest. The agent must notice the flip mid-checkout and switch. Graded on
    the OUTCOME (positive end-state checks; milestones are sticky):
      env gate -> flip_delivered (async event fired) + valuemart_now_cheapest
      used     -> ordered_gear_on_valuemart (laptop + keyboard, the cheaper
                  store post-flip) + applied_valuemart30 (used the new coupon).
    Failure = barrelled through the ShopGym order (sunk cost), or bought
    ValueMart without the flip coupon."""
    from server.mutations import SHIPPING_FLAT
    from server.apps import bus as _bus
    _GEAR_VM = {"vm_laptop_studio", "vm_kb_mech"}

    def _vm_gear_orders(p: Probe) -> list:
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return []
        return [o for o in mk.orders.values()
                if _GEAR_VM.issubset({it.product_id for it in o.items})]

    def _ordered_gear_on_valuemart(p: Probe) -> bool:
        return len(_vm_gear_orders(p)) >= 1

    def _applied_valuemart30(p: Probe) -> bool:
        return any(o.coupon_code == "VALUEMART30" for o in _vm_gear_orders(p))

    def _flip_delivered(p: Probe) -> bool:
        return p.world is not None and _bus.has_delivered(p.world, "CouponFlipAlert")

    def _valuemart_now_cheapest(p: Probe) -> bool:
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return False
        vlap, vkb = mk.products.get("vm_laptop_studio"), mk.products.get("vm_kb_mech")
        slap = p.state.products.get("p_laptop_studio")
        skb = p.state.products.get("p_kb_mech")
        if not (vlap and vkb and slap and skb):
            return False
        vm_sub = vlap.price + vkb.price
        c = mk.coupons.get("VALUEMART30")
        vm_total = round(vm_sub - (vm_sub * c.percent_off if c else 0), 2) \
            + mk.delivery_for(vm_sub)
        shop_total = round((slap.base_price + skb.base_price) * 0.80, 2) + SHIPPING_FLAT
        return vm_total < shop_total

    return TaskSuite(
        task_id="M18/async_coupon_flip",
        milestones=[
            Milestone("flip_delivered", weight=0.0,
                      check=_flip_delivered, required_for_success=False),
            Milestone("valuemart_now_cheapest", weight=0.0,
                      check=_valuemart_now_cheapest, required_for_success=False),
            Milestone("ordered_gear_on_valuemart", weight=0.5,
                      check=_ordered_gear_on_valuemart, required_for_success=True),
            Milestone("applied_valuemart30", weight=0.5,
                      check=_applied_valuemart30, required_for_success=True),
        ],
    )


def _suite_m17() -> TaskSuite:
    """CROSS-RETAILER comparison + inbox coupon. The monitor is on both stores;
    the emailed VALUE10 coupon makes ValueMart the genuinely-cheaper store
    (price + delivery - coupon, pre-tax). Grade the OUTCOME with positive
    end-state checks (milestones are sticky, so a 'not bought on X' negative
    would wrongly fire at step 0):
      env gate -> valuemart_is_cheaper (the engineered answer holds)
      used     -> ordered_monitor_on_valuemart (picked the cheaper store)
                  + applied_value10_coupon (read + used the emailed coupon;
                    without it ValueMart isn't actually cheaper)."""
    from server.mutations import SHIPPING_FLAT
    _MON_SHOP = "p_monitor_24"
    _MON_VM = "vm_monitor_24"

    def _shop_deal(p):
        prod = p.state.products.get(_MON_SHOP)
        return (prod.base_price + SHIPPING_FLAT) if prod else None

    def _vm_deal(p):
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return None
        prod = mk.products.get(_MON_VM)
        if prod is None:
            return None
        c = mk.coupons.get("VALUE10")               # best achievable price here
        disc = round(prod.price * c.percent_off, 2) if c else 0.0
        return round(prod.price - disc + mk.delivery_for(prod.price), 2)

    def _valuemart_cheaper(p) -> bool:
        sd, vd = _shop_deal(p), _vm_deal(p)
        return sd is not None and vd is not None and vd < sd

    def _vm_monitor_orders(p):
        mk = getattr(p.world, "market", None) if p.world else None
        if mk is None:
            return []
        return [o for o in mk.orders.values()
                if any(it.product_id == _MON_VM for it in o.items)]

    def _ordered_monitor_on_valuemart(p) -> bool:
        return len(_vm_monitor_orders(p)) >= 1

    def _applied_value10_coupon(p) -> bool:
        return any(o.coupon_code == "VALUE10" for o in _vm_monitor_orders(p))

    return TaskSuite(
        task_id="M17/cross_retailer_cheaper",
        milestones=[
            Milestone("valuemart_is_cheaper", weight=0.0,
                      check=_valuemart_cheaper, required_for_success=False),
            Milestone("ordered_monitor_on_valuemart", weight=0.5,
                      check=_ordered_monitor_on_valuemart,
                      required_for_success=True),
            Milestone("applied_value10_coupon", weight=0.5,
                      check=_applied_value10_coupon, required_for_success=True),
        ],
    )


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

SUITE_FACTORIES = {
    "A1/buy_wireless_mouse":     _suite_a1,
    "A2/filter_laptop":          _suite_a2,
    "A3/configure_bundle":       _suite_a3,
    "A4/home_office_bundle":     _suite_a4,
    "B1/add_address":            _suite_b1,
    "B2/track_and_return":       _suite_b2,
    "B3/account_overhaul":       _suite_b3,
    "B4/subscription_juggle":    _suite_b4,
    "C1/promo_partial":          _suite_c1,
    "C2/split_shipping_gift":    _suite_c2,
    "C3/subscription_loyalty":   _suite_c3,
    "C4/mega_checkout":          _suite_c4,
    "D1/browse_audio_no_search":     _suite_d1,
    "D2/drill_electronics_keyboards": _suite_d2,
    "M2/order_then_track_via_email": _suite_m2,
    "M3/dinner_then_receipt":        _suite_m3,
    "M4/order_then_reply_total":     _suite_m4,
    "M5/cheaper_mouse_from_deals":   _suite_m5,
    "M6/reorder_bigger_order":       _suite_m6,
    "M7/dinner_and_host_gift":       _suite_m7,
    "M8/spending_audit_branch":      _suite_m8,
    "M9/calendar_gated_dinner":      _suite_m9,
    "M10/dinner_source_conflict":    _suite_m10,
    "M11/cancel_unshipped_over_100": _suite_m11,
    "M12/bulk_add_dense_grid":       _suite_m12,
    "M13/order_cleanup_audit":       _suite_m13,
    "M14/return_then_refund":        _suite_m14,
    "M15/inbox_price_watch":         _suite_m15,
    "M16/coordinated_dinner_delay":  _suite_m16,
    "M17/cross_retailer_cheaper":    _suite_m17,
    "M18/async_coupon_flip":         _suite_m18,
    "M19/coupon_minefield":          _suite_m19,
    "M20/errand_run":                _suite_m20,
    "M21/async_errand_run":          _suite_m21,
    "M22/async_calendar_cascade":    _suite_m22,
    "M23/offsite_keeps_moving":      _suite_m23,
    "M24/procurement_puzzle":        _suite_m24,
    "M25/dispatch_desk":             _suite_m25,
    "M26/calendar_purge_async":      _suite_m26,
}


def build_suite(task_id: str) -> TaskSuite:
    if task_id not in SUITE_FACTORIES:
        raise KeyError(f"no verifier suite for {task_id}")
    return SUITE_FACTORIES[task_id]()
