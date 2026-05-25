"""Task factories — each builds a fresh GymState for one episode.

Three categories, 9 tasks total:

  A. Product discovery & purchase     (A1 easy, A2 medium, A3 hard)
  B. Account & order management       (B1 easy, B2 medium, B3 hard)
  C. Complex checkout & promotions    (C1 medium, C2 medium, C3 hard)

Each factory:
  * builds the user(s) the agent will use (with pre-set login creds)
  * picks the catalog slice that's relevant for this task
  * configures promotions / pre-existing orders / pre-existing
    subscriptions as needed by the task

Verifiers (in ``server/verifiers.py``) consume the task_id to look up
the right ordered list of milestones.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from typing import TYPE_CHECKING

from server import catalog
from server.state import (
    Address, GymState, Order, OrderItem, PaymentMethod, Product, Promotion,
    Shipment, ShipmentEvent, User,
)

if TYPE_CHECKING:
    from server.apps.world import WorldState


# --------------------------------------------------------------------------- #
# Default fixtures
# --------------------------------------------------------------------------- #

def _alice() -> User:
    """The default user. Tasks that need a logged-in user often use this."""
    u = User(
        id="u_alice", email="alice@example.com",
        password="password123", full_name="Alice Anderson",
        loyalty_tier="gold",
    )
    u.addresses["addr_home"] = Address(
        id="addr_home", label="Home", full_name="Alice Anderson",
        line1="100 Park Avenue", line2="Apt 4B",
        city="Brooklyn", state="NY", zip="11201", is_default=True,
    )
    u.addresses["addr_work"] = Address(
        id="addr_work", label="Work", full_name="Alice Anderson",
        line1="500 Madison Avenue", line2="22nd Floor",
        city="New York", state="NY", zip="10022", is_default=False,
    )
    u.payment_methods["pay_visa"] = PaymentMethod(
        id="pay_visa", label="Visa ****4242",
        kind="credit_card", expires="08/27", is_default=True,
    )
    u.payment_methods["pay_paypal"] = PaymentMethod(
        id="pay_paypal", label="PayPal (alice@example.com)",
        kind="paypal", is_default=False,
    )
    return u


# --------------------------------------------------------------------------- #
# Brief copy (these are what shows up in the task banner)
# --------------------------------------------------------------------------- #

# Briefs are written the way a REAL USER would phrase a request — natural
# language with intent and context, NOT spoon-fed "(NOT the X, NOT the Y)"
# disambiguation. The agent has to interpret the intent and decide which
# product/option matches, just like a human shopper would. Adversarial
# look-alikes in the catalog (gaming mouse, office-category monitor, dog
# treats vs food, Studio Laptop vs Studio Laptop Pro, etc.) are the traps
# the agent must reason past on its own.
BRIEFS = {
    "A1": (
        "I need a basic wireless mouse for my office desk — just the "
        "standard model for everyday clicking, nothing specialized. "
        "Order one for me, ship it to my home, and put it on my Visa."
    ),
    "A2": (
        "I'm shopping for a reliable laptop. My budget tops out at "
        "$1,000, and I only buy well-reviewed products — 4.5 stars or "
        "better. Find one that fits and buy it. Ship it home and charge "
        "my Visa."
    ),
    "A3": (
        "I'm putting together a work setup. Get me the Studio Laptop "
        "configured with the most memory and storage it offers — I want "
        "32GB of RAM and a 1TB SSD. Add a wireless mouse and a mechanical "
        "keyboard to go with it. Keep the whole cart under $1,900. Ship "
        "everything home and pay with my Visa."
    ),

    "B1": (
        "Add my beach house to my saved addresses — it's at 17 Ocean "
        "Drive, Montauk, NY 11954, under my name, Alice Anderson. From "
        "now on I want everything shipped there by default."
    ),
    "B2": (
        "The wireless mouse from my order ORDER_REF_HERE stopped working "
        "— it's defective. Pull up that order and check the tracking so I "
        "know it actually got delivered, then start a return for just the "
        "mouse and refund it back to my original payment method."
    ),
    "B3": (
        "Tidy up my account for me, please. Make my Work address the "
        "default for shipping. Add a backup credit card — number "
        "4111 1111 1111 1111, expiring 12/29, CVV 123 — and make that my "
        "default way to pay. And turn on two-factor authentication; use "
        "123456 as the verification code."
    ),

    "C1": (
        "Grab me a Studio Laptop and a plain cotton t-shirt. I've got a "
        "promo code, TECH20, that takes money off electronics — apply it "
        "at checkout. Ship the order to my home and pay with my Visa."
    ),
    "C2": (
        "I'm buying two things and they go to different places. The "
        "Bluetooth headphones — the studio pair — are a birthday gift for "
        "a friend: send them to my home address, gift-wrapped, with the "
        "note 'Happy birthday'. The wireless mouse is for me at the "
        "office, so ship that one to my work address, no gift wrap. Put "
        "it all on my Visa."
    ),
    "C3": (
        "Set me up on auto-delivery for the premium dog food — once a "
        "week, four deliveries to start. Ship it home and bill my Visa. "
        "I'm a gold member, so I should be getting my loyalty discount "
        "automatically on each delivery."
    ),

    # ──────────────────────────────────────────────────────────────
    # VERY HARD tasks — multi-step, multi-constraint, real-user phrasing.
    # No "(NOT the X)" hand-holding: the agent must infer which product
    # and option each natural description points to.
    # ──────────────────────────────────────────────────────────────

    "A4": (
        "I'm setting up a new home office and need four things: a large "
        "27-inch monitor, a proper mechanical keyboard with a good typing "
        "feel, a comfortable mouse that won't wreck my wrist on long days, "
        "and a fast USB-C charger. I've got $550 for the whole lot, so "
        "keep it under that. Ship everything to my work address — I'm "
        "there during the day — and use my PayPal; I'm saving the credit "
        "card for something else this month."
    ),

    "B4": (
        "I'm switching my dog from kibble over to treats, so a few things "
        "in my account. First, cancel my current premium dog food "
        "subscription. Then set me up on a new one for the premium dog "
        "treats — every two weeks, six deliveries, shipped to my work "
        "address and billed to PayPal. While you're in there, turn on "
        "two-factor authentication for me; the code is 123456. Oh, and I "
        "changed my mind about the Bluetooth speaker from my recent order "
        "— send just the speaker back (keep the mouse, that one's great) "
        "and take store credit, since there's a 5% bonus for it."
    ),

    "C4": (
        "Big order, bear with me. I need a Studio Laptop, a black cotton "
        "t-shirt in medium, and a basic wireless mouse. The laptop ships "
        "to my work address. The t-shirt is a birthday present for my mom "
        "— send it to my home, gift-wrapped, with the message 'Happy "
        "Birthday Mom!'. The mouse goes home too, but no gift wrap on "
        "that. I've got a TECH20 promo code for the electronics discount "
        "— apply it. Pay with my Visa and place the order."
    ),

    # ──────────────────────────────────────────────────────────────
    # TAXONOMY-NAVIGATION tasks — the agent must BROWSE the category /
    # subcategory tree to find products, the way a shopper browses when
    # they don't know the exact product name. Searching the search bar
    # is the lazy shortcut these tasks are designed to discourage.
    # ──────────────────────────────────────────────────────────────

    "D1": (
        "I'm in the mood to browse rather than search for something "
        "specific. Take me through the Audio department, look at the "
        "headphones, and pick out a well-reviewed pair — 4.5 stars or "
        "better. Buy it, ship it home, and use my Visa. (I'd rather you "
        "browse the store than type in the search box.)"
    ),

    "D2": (
        "Walk me through the Electronics department to the keyboards "
        "section — I want to see what's there rather than search. Pick "
        "me out a proper mechanical keyboard with real tactile feedback, "
        "not one of the cheap membrane ones. Buy it, ship home, pay with "
        "Visa."
    ),

    # ──────────────────────────────────────────────────────────────
    # CROSS-APP tasks (category "M") — one journey spanning several apps
    # (Shop / Mail / Food), the way a real person juggles browser tabs.
    # The hard part is carrying a fact across the app boundary (an order
    # id, a receipt) and acting on the RIGHT one.
    # ──────────────────────────────────────────────────────────────

    "M2": (
        "I need a basic wireless mouse — just the standard everyday one, "
        "nothing fancy. Order it for me. Then I want to know where my "
        "package is: find the order confirmation in my email and use the "
        "tracking link in it to check the delivery status."
    ),

    "M3": (
        "I'm hungry — order me some dinner tonight from the food app, "
        "whatever looks good from one place. Once it's placed, hop over to "
        "my email and open the receipt so we know it actually went through."
    ),

    "M4": (
        "Order me a basic wireless mouse — the standard everyday one. Once "
        "it's ordered, reply to the order-confirmation email and tell them "
        "the exact total you were charged — the full amount with tax and "
        "shipping, not the sticker price — so they can reconcile my receipt."
    ),

    "M5": (
        "I have two promotional emails in my inbox, each advertising a "
        "different computer mouse at a sale price. I only want to buy one "
        "mouse: whichever of those two is the cheaper deal. Work out which "
        "one that is, then order it — ship it to my home address and pay "
        "with my Visa."
    ),

    "M6": (
        "Two of my past order confirmations are sitting in my email. "
        "Whichever of those two orders had the higher total, I'd like to "
        "buy everything in it again — but skip any item that's no longer "
        "in stock. Put those items back in the cart and place the order, "
        "then reply to that same confirmation email telling me exactly "
        "which items you reordered."
    ),

    "M7": (
        "I'm hosting a small dinner tonight and need two things handled. "
        "First, order us some food from a single restaurant in the food "
        "app — keep the food total under $35. Second, pick up a host gift "
        "in the shop: it has to be a book, rated at least 4.5 stars, and "
        "under $20. Once both are sorted, reply to Alex's dinner email and "
        "let them know roughly when the food will arrive and which book "
        "you chose."
    ),

    "M8": (
        "Go through the order confirmations in my email and add up the "
        "totals of all my past shop orders. If they come to more than "
        "$1,000, I've been overspending this month — so DON'T buy anything "
        "new; instead, reply to the confirmation of my single most "
        "expensive order asking them to cancel it. But if the total is "
        "$1,000 or less, treat yourself: order a coffee from the food app "
        "and reply to my cheapest order's confirmation with a quick "
        "thank-you."
    ),

    "M9": (
        "Quick one about tomorrow evening: check my calendar and see "
        "whether I'm free after 6pm tomorrow. If I am free, order us dinner "
        "from the food app, add a calendar event for when it's due to "
        "arrive, and email Alex to confirm we're on for dinner tomorrow "
        "evening. If I'm NOT free tomorrow evening, don't order anything — "
        "just email Alex asking whether we can move it to Thursday instead."
    ),

    "M10": (
        "Alex and I are trying to do dinner tomorrow evening. Before you do "
        "anything, check BOTH of these: my calendar (am I free after 6pm "
        "tomorrow?) and Alex's latest email (Alex may have an update on their "
        "end). Only go ahead and order dinner from the food app if BOTH work "
        "out — my evening is open AND Alex can still make it tomorrow — and "
        "then email Alex to confirm. If either one doesn't work, don't order "
        "anything; just reply to Alex to sort out another day that works for "
        "us both."
    ),

    "M11": (
        "I need to clean up my pending orders. Go through my order-confirmation "
        "emails and cancel the ones that are BOTH over $100 AND haven't shipped "
        "yet — for each of those, open the order's email and reply asking to "
        "cancel it. Leave everything else exactly as it is: don't touch any "
        "order that has already shipped, and don't touch any order that's $100 "
        "or under. Make sure you get every one that qualifies and nothing that "
        "doesn't."
    ),

    "M12": (
        "You're on the Quick Order grid. Add EVERY mouse and EVERY keyboard "
        "shown here to the cart by tapping its Add button — and nothing else. "
        "Don't add laptops, monitors, chargers, smartwatches, trackpads, or "
        "anything that isn't a mouse or a keyboard. Get every qualifying item, "
        "and don't add a single one that doesn't qualify."
    ),
}


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def _base_state(seed: int, task_id: str, difficulty: str,
                category: str, with_login: bool = False) -> GymState:
    state = GymState(
        task_id=task_id, seed=seed,
        task_brief=BRIEFS[task_id.split("/")[0]],
        task_difficulty=difficulty,                      # type: ignore[arg-type]
        task_category=category,                          # type: ignore[arg-type]
    )
    state.products = catalog._build_catalog()
    state.users = {"u_alice": _alice()}
    if with_login:
        state.current_user_id = "u_alice"
    return state


# ----- Category A: product discovery & purchase ---------------------------- #

def task_a1_buy_wireless_mouse(seed: int) -> GymState:
    return _base_state(
        seed, "A1/buy_wireless_mouse", "easy", "A", with_login=True,
    )


def task_a2_filter_laptop(seed: int) -> GymState:
    # Build the catalog and tweak laptop prices for this seed within
    # ranges that preserve the constraint (one valid laptop only).
    rng = random.Random(seed)
    state = _base_state(seed, "A2/filter_laptop", "medium", "A",
                        with_login=True)
    # Studio laptop is the "right" choice — $899.99, 4.6 rating
    state.products["p_laptop_studio"].base_price = round(
        rng.uniform(799.0, 989.0), 2,
    )
    return state


def task_a3_configure_bundle(seed: int) -> GymState:
    state = _base_state(
        seed, "A3/configure_bundle", "hard", "A", with_login=True,
    )
    # A3 specifically requires the variant-picker flow. We add variants
    # to the Studio Laptop only for this task.
    from server.state import ProductVariant
    state.products["p_laptop_studio"].variants = [
        ProductVariant("v_lt_16_512", "16GB RAM / 512GB SSD",
                       {"ram": "16GB", "storage": "512GB"}, 0.0, 6),
        ProductVariant("v_lt_16_1tb", "16GB RAM / 1TB SSD",
                       {"ram": "16GB", "storage": "1TB"}, 150.0, 4),
        ProductVariant("v_lt_32_1tb", "32GB RAM / 1TB SSD",
                       {"ram": "32GB", "storage": "1TB"}, 400.0, 2),
    ]
    return state


# ----- Category B: account & order management ------------------------------ #

def task_b1_add_address(seed: int) -> GymState:
    return _base_state(seed, "B1/add_address", "easy", "B",
                       with_login=True)


def task_b2_track_and_return(seed: int) -> GymState:
    """Seeds an order so the agent has something to return."""
    state = _base_state(seed, "B2/track_and_return", "medium", "B",
                        with_login=True)
    # Pre-create an order with 2 items to make the task realistic.
    alice = state.users["u_alice"]
    addr = list(alice.addresses.values())[0]
    pay = list(alice.payment_methods.values())[0]
    items = [
        OrderItem(
            id="ln_mouse", product_id="p_mouse_wireless",
            product_name="Wireless Mouse", variant_id=None,
            variant_label="", quantity=1, unit_price=29.99,
            gift_wrap=False, gift_message="",
            ship_to_address_id=addr.id, scheduled_delivery=None,
        ),
        OrderItem(
            id="ln_speaker", product_id="p_speaker",
            product_name="Bluetooth Speaker", variant_id=None,
            variant_label="", quantity=1, unit_price=79.99,
            gift_wrap=False, gift_message="",
            ship_to_address_id=addr.id, scheduled_delivery=None,
        ),
    ]
    sh = Shipment(
        id="sh_existing",
        tracking_number="1Z999AA10123456784",
        carrier="UPS",
        item_ids=[i.id for i in items],
        status="delivered",
        estimated_delivery=(
            datetime.now(timezone.utc) - timedelta(days=2)
        ).date().isoformat(),
        events=[
            ShipmentEvent("2024-01-01T10:00:00Z", "label_created",
                          "Distribution Center", "Shipping label created"),
            ShipmentEvent("2024-01-02T08:00:00Z", "in_transit",
                          "Newark, NJ", "In transit"),
            ShipmentEvent("2024-01-03T14:20:00Z", "delivered",
                          "Brooklyn, NY", "Delivered to mailbox"),
        ],
    )
    state.orders["ORD-EXISTING-1234"] = Order(
        id="ORD-EXISTING-1234", user_id="u_alice",
        placed_at="2024-01-01T09:30:00Z",
        items=items,
        subtotal=109.98, discount=0.0,
        tax=round(109.98 * 0.085, 2),
        shipping=5.99, total=round(109.98 * 1.085 + 5.99, 2),
        promo_code=None, payment_id=pay.id, status="delivered",
        shipments=[sh],
    )
    # Patch the brief to reference the actual order id.
    state.task_brief = BRIEFS["B2"].replace(
        "ORDER_REF_HERE", "ORD-EXISTING-1234",
    )
    return state


def task_b3_account_overhaul(seed: int) -> GymState:
    return _base_state(seed, "B3/account_overhaul", "hard", "B",
                       with_login=True)


# ----- Category C: complex checkout ---------------------------------------- #

def _promos_for_c1() -> dict[str, Promotion]:
    return {
        "TECH20": Promotion(
            code="TECH20", name="20% off electronics",
            description="20% off all electronics. Cannot combine with "
                        "other promotions.",
            discount_pct=0.20,
            applies_to_category="electronics",
            min_purchase=0.0,
            description_fineprint=(
                "Discount applied to the eligible line items only "
                "(electronics). Other items are charged at full price."
            ),
        ),
        "BIGSAVE50": Promotion(
            code="BIGSAVE50", name="$50 off $500+",
            description="$50 off when you spend over $500.",
            discount_flat=50.0, min_purchase=500.0,
        ),
        "EXPIRED10": Promotion(
            code="EXPIRED10", name="(expired) 10% off",
            description="This promo has expired.",
            discount_pct=0.10, expired=True,
        ),
    }


def task_c1_promo_partial(seed: int) -> GymState:
    state = _base_state(seed, "C1/promo_partial", "medium", "C",
                        with_login=True)
    state.promotions = _promos_for_c1()
    return state


def task_c2_split_shipping(seed: int) -> GymState:
    return _base_state(seed, "C2/split_shipping_gift", "medium", "C",
                       with_login=True)


def task_c3_subscription(seed: int) -> GymState:
    return _base_state(seed, "C3/subscription_loyalty", "hard", "C",
                       with_login=True)


# --------------------------------------------------------------------------- #
# VERY HARD tasks — added May 2026. One per category. Each is designed to
# stress multiple edge-case clusters simultaneously:
#   - heavy adversarial product naming
#   - constraints across multiple dimensions (price + category + brand)
#   - multi-step sequences with order dependencies
#   - non-default address / non-default payment
# --------------------------------------------------------------------------- #

def task_a4_home_office_bundle(seed: int) -> GymState:
    """4-product bundle with strict constraints — tests filtering,
    distractor avoidance across multiple product types, budget math,
    non-default address + non-default payment."""
    return _base_state(seed, "A4/home_office_bundle", "hard", "A",
                       with_login=True)


def task_b4_subscription_juggle(seed: int) -> GymState:
    """Multi-flow account task: cancel an existing subscription,
    create a new one (different cadence/payment/address), enable 2FA,
    initiate a partial return — all in one session.

    Pre-seeds: an active Dog Food subscription + an existing order
    with both a mouse and a speaker the agent can return.
    """
    state = _base_state(seed, "B4/subscription_juggle", "hard", "B",
                        with_login=True)
    from server.state import Subscription
    alice = state.users["u_alice"]
    addr = alice.addresses["addr_home"]
    pay = alice.payment_methods["pay_visa"]

    # Pre-existing active Dog Food subscription that agent must cancel
    state.subscriptions["sub_existing_dogfood"] = Subscription(
        id="sub_existing_dogfood", user_id="u_alice",
        product_id="p_pet_food", variant_id=None, quantity=1,
        cadence="weekly", deliveries_remaining=3,
        next_delivery_date="2026-06-01",
        address_id=addr.id, payment_id=pay.id,
        loyalty_discount_pct=0.10, status="active",
    )

    # Pre-existing order with mouse + speaker for the return flow
    items = [
        OrderItem(id="ln_mouse", product_id="p_mouse_wireless",
                  product_name="Wireless Mouse", variant_id=None,
                  variant_label="", quantity=1, unit_price=29.99,
                  gift_wrap=False, gift_message="",
                  ship_to_address_id=addr.id, scheduled_delivery=None),
        OrderItem(id="ln_speaker", product_id="p_speaker",
                  product_name="Bluetooth Speaker", variant_id=None,
                  variant_label="", quantity=1, unit_price=79.99,
                  gift_wrap=False, gift_message="",
                  ship_to_address_id=addr.id, scheduled_delivery=None),
    ]
    sh = Shipment(
        id="sh_b4", tracking_number="1Z999AA20987654321",
        carrier="UPS",
        item_ids=[i.id for i in items],
        status="delivered",
        estimated_delivery=(
            datetime.now(timezone.utc) - timedelta(days=5)
        ).date().isoformat(),
        events=[
            ShipmentEvent("2026-05-01T10:00:00Z", "label_created",
                          "Distribution Center", "Shipping label created"),
            ShipmentEvent("2026-05-03T14:20:00Z", "delivered",
                          "Brooklyn, NY", "Delivered"),
        ],
    )
    state.orders["ORD-B4-9999"] = Order(
        id="ORD-B4-9999", user_id="u_alice",
        placed_at="2026-05-01T09:30:00Z",
        items=items,
        subtotal=109.98, discount=0.0,
        tax=round(109.98 * 0.085, 2),
        shipping=5.99, total=round(109.98 * 1.085 + 5.99, 2),
        promo_code=None, payment_id=pay.id, status="delivered",
        shipments=[sh],
    )
    return state


def task_c4_mega_checkout(seed: int) -> GymState:
    """The hardest checkout task — combines C1 (promo on right line) +
    C2 (split shipping + gift wrap) + variant selection on the t-shirt.
    Three line items, three different shipping/gift-wrap configurations,
    a category-restricted promo, and a non-default payment vs address mix.
    """
    state = _base_state(seed, "C4/mega_checkout", "hard", "C",
                        with_login=True)
    state.promotions = _promos_for_c1()
    return state


# ----- Category D: taxonomy navigation ------------------------------------- #

def task_d1_browse_audio(seed: int) -> GymState:
    """Browse the Audio category -> headphones subcategory, no search."""
    return _base_state(seed, "D1/browse_audio_no_search", "medium", "D",
                       with_login=True)


def task_d2_drill_keyboards(seed: int) -> GymState:
    """Drill Electronics -> keyboards subcategory, pick a mechanical one."""
    return _base_state(seed, "D2/drill_electronics_keyboards", "hard", "D",
                       with_login=True)


# ----- Category M: cross-app journeys (Shop / Mail / Food) ----------------- #
# These factories return a WorldState (shop GymState + the per-app stores),
# not a bare GymState, because the journey spans apps. The shop half is built
# with the same _base_state() the single-app tasks use (logged-in Alice + the
# full catalog); the mail/food stores get their default seeds.

def _cross_app_world(seed: int, task_id: str, difficulty: str) -> "WorldState":
    from server.apps.world import WorldState
    from server.apps.mail.state import make_mailstate
    from server.apps.food.state import make_foodstate
    from server.apps.calendar.state import make_calendarstate
    shop = _base_state(seed, task_id, difficulty, "M", with_login=True)
    return WorldState(
        shop=shop, mail=make_mailstate(seed), food=make_foodstate(seed),
        calendar=make_calendarstate(seed),
    )


def task_m2_order_then_track(seed: int) -> "WorldState":
    """North-star: order the standard wireless mouse, then find the order-
    confirmation email and use ITS tracking link. Spans Shop -> Mail ->
    (back to) Shop tracking; the agent has to carry the order id across the
    tab switch and act on the right one."""
    return _cross_app_world(seed, "M2/order_then_track_via_email", "hard")


def task_m3_dinner_then_receipt(seed: int) -> "WorldState":
    """Order dinner from the Food app, then open the receipt email it
    generates. Spans Food -> Mail."""
    return _cross_app_world(seed, "M3/dinner_then_receipt", "medium")


def task_m4_order_then_reply_total(seed: int) -> "WorldState":
    """Difficulty lever: order the mouse, then REPLY to the confirmation
    email with the exact CHARGED total (subtotal + tax + shipping). The trap
    is that the charged total != the sticker price, so an agent that doesn't
    actually open + read the email replies with the wrong number. Spans
    Shop -> Mail (compose), with a precise value carried across the hop."""
    return _cross_app_world(seed, "M4/order_then_reply_total", "hard")


def _seed_past_order(shop, *, order_id, items, addr_id, pay_id):
    """Helper: create a delivered past order from a list of OrderItems."""
    subtotal = round(sum(it.unit_price * it.quantity for it in items), 2)
    shop.orders[order_id] = Order(
        id=order_id, user_id="u_alice", placed_at="2026-05-01T10:00:00Z",
        items=items, subtotal=subtotal, discount=0.0,
        tax=round(subtotal * 0.085, 2), shipping=5.99,
        total=round(subtotal * 1.085 + 5.99, 2),
        promo_code=None, payment_id=pay_id, status="delivered",
    )
    return shop.orders[order_id]


def task_m6_reorder_bigger_order(seed: int) -> "WorldState":
    """BRUTAL multi-step: two past orders (with confirmation emails) of
    different totals. The agent must compare the totals, reorder ALL items
    of the BIGGER order (skipping the out-of-stock one), place it, and reply
    to that order's email listing what it reordered. Memory + comparison +
    multi-item + conditional (OOS) + carry-the-list-back across apps."""
    from server.apps.mail.state import Email, SEED_DATE
    world = _cross_app_world(seed, "M6/reorder_bigger_order", "hard")
    shop = world.shop
    addr = "addr_home"
    pay = "pay_visa"

    def _oi(lid, pid, name, price):
        return OrderItem(
            id=lid, product_id=pid, product_name=name, variant_id=None,
            variant_label="", quantity=1, unit_price=price,
            gift_wrap=False, gift_message="",
            ship_to_address_id=addr, scheduled_delivery=None,
        )

    # Order A (SMALLER): one wireless mouse.
    oa = _seed_past_order(
        shop, order_id="ORD-PAST-A",
        items=[_oi("a_mouse", "p_mouse_wireless", "Wireless Mouse", 29.99)],
        addr_id=addr, pay_id=pay,
    )
    # Order B (BIGGER): laptop + keyboard + charger. Charger goes OOS, so the
    # correct reorder is laptop + keyboard only.
    ob = _seed_past_order(
        shop, order_id="ORD-PAST-B",
        items=[
            _oi("b_laptop", "p_laptop_studio", "Studio Laptop 14", 899.99),
            _oi("b_kb", "p_kb_mech", "Mechanical Keyboard", 119.99),
            _oi("b_charger", "p_charger", "USB-C Fast Charger 65W", 29.99),
        ],
        addr_id=addr, pay_id=pay,
    )
    shop.products["p_charger"].stock = 0     # now out of stock -> must be skipped

    # Confirmation emails (so the totals live in Mail, not the shop UI).
    m = world.mail
    for oid, order, label in [("ORD-PAST-A", oa, "9:10 AM"),
                              ("ORD-PAST-B", ob, "9:40 AM")]:
        eid = m.new_id()
        lines = "\n".join(f"  {it.quantity} x {it.product_name}"
                          for it in order.items)
        m.inbox[eid] = Email(
            id=eid, sender="orders@shopgym.com", to=m.account_email,
            subject=f"Your ShopGym order {oid} is confirmed",
            body=(f"Thanks for your order!\n\nOrder number: {oid}\n"
                  f"Items:\n{lines}\n\nOrder total: ${order.total:.2f}\n"),
            received_at=f"{SEED_DATE}T09:00:00", received_label=label,
            read=False, labels=["orders"],
            order_id=oid, amount_total=order.total,
        )
    return world


def task_m7_dinner_and_host_gift(seed: int) -> "WorldState":
    """BRUTAL 3-app: order food under $35 (Food) + buy a host gift that is a
    book rated >=4.5 AND under $20 (Shop; only ONE of three books qualifies)
    + reply to Alex's dinner email with BOTH the food ETA and the book name
    (Mail). Budget + multi-constraint selection + 2-fact memory across apps."""
    world = _cross_app_world(seed, "M7/dinner_and_host_gift", "hard")
    shop = world.shop
    # Set book ratings so EXACTLY ONE book qualifies (>=4.5 AND <$20):
    #   p_book_sci_fi  "Project Hail Mary"  $16.50  -> 4.7  QUALIFIES
    #   p_book_history "Sapiens"            $19.99  -> 4.2  fails rating
    #   p_book_cook    "The Joy of Cooking" $24.99  -> 4.8  fails price
    shop.products["p_book_sci_fi"].rating = 4.7
    shop.products["p_book_history"].rating = 4.2
    shop.products["p_book_cook"].rating = 4.8
    return world


def task_m8_spending_audit_branch(seed: int) -> "WorldState":
    """HARDEST: aggregation + conditional branch + superlative + 'don't do
    the other branch'. Three past shop orders (totals in the emails) sum to
    $1,319.92 (> $1,000), so the correct branch is: buy NOTHING new and reply
    to the MOST EXPENSIVE order (ORD-P2, $982.48) asking to cancel it. Traps:
    miscompute the sum -> wrong branch; pick the wrong order; take the easy
    'treat yourself' branch; or do nothing."""
    from server.apps.mail.state import Email, SEED_DATE
    world = _cross_app_world(seed, "M8/spending_audit_branch", "hard")
    shop = world.shop
    addr, pay = "addr_home", "pay_visa"

    def _oi(lid, pid, name, price):
        return OrderItem(
            id=lid, product_id=pid, product_name=name, variant_id=None,
            variant_label="", quantity=1, unit_price=price, gift_wrap=False,
            gift_message="", ship_to_address_id=addr, scheduled_delivery=None)

    specs = [
        ("ORD-P1", [_oi("p1a", "p_mouse_wireless", "Wireless Mouse", 29.99),
                    _oi("p1b", "p_hp_studio", "Bluetooth Headphone Studio", 149.99)]),
        ("ORD-P2", [_oi("p2a", "p_laptop_studio", "Studio Laptop 14", 899.99)]),  # most expensive
        ("ORD-P3", [_oi("p3a", "p_kb_mech", "Mechanical Keyboard", 119.99)]),
    ]
    m = world.mail
    for oid, items in specs:
        o = _seed_past_order(shop, order_id=oid, items=items,
                             addr_id=addr, pay_id=pay)
        eid = m.new_id()
        lines = "\n".join(f"  {it.quantity} x {it.product_name}"
                          for it in o.items)
        m.inbox[eid] = Email(
            id=eid, sender="orders@shopgym.com", to=m.account_email,
            subject=f"Your ShopGym order {oid} is confirmed",
            body=(f"Order {oid}\nItems:\n{lines}\n\n"
                  f"Order total: ${o.total:.2f}\n"),
            received_at=f"{SEED_DATE}T08:00:00", received_label="8:00 AM",
            read=False, labels=["orders"], order_id=oid, amount_total=o.total)
    return world


def task_m9_calendar_gated_dinner(seed: int) -> "WorldState":
    """4-app, free/busy-GATED, multi-step branch. The seeded calendar leaves
    TOMORROW EVENING free (events at 10am + 2pm tomorrow), so the correct
    branch is the HARD one: order dinner (Food) + add a delivery event
    (Calendar) + email Alex to CONFIRM (Mail) — three actions across three
    apps after first CHECKING the calendar. Trap: assume busy / skip the
    check -> propose Thursday (wrong branch) and order nothing."""
    return _cross_app_world(seed, "M9/calendar_gated_dinner", "hard")


# M10 — source-of-truth conflict. The calendar is ALWAYS free tomorrow
# evening (the salient, structured "go" signal). What flips with the seed is
# Alex's email: even seeds confirm, odd seeds carry a conflict that OVERRIDES
# the free calendar. Both emails open conversationally and both mention
# "tomorrow evening", so the agent has to read the WHOLE body — the conflict
# lives in the detail, not the subject line. "another day" is the stable
# sentinel the verifier/facts/oracle key on (it appears only in the conflict).
_M10_ALEX_BENIGN = (
    "Hey! Just confirming we're still on for dinner tomorrow evening — my "
    "whole evening is open and I'm really looking forward to it. Tell me "
    "where to meet and I'll be there. — Alex"
)
_M10_ALEX_CONFLICT = (
    "Hey — bit of bad news. My flight back from the Denver conference got "
    "pushed and I won't land until around 9pm tomorrow, so I can't make "
    "dinner tomorrow evening after all. Could we find another day — maybe "
    "Thursday? Really sorry for the late notice. — Alex"
)


def _m10_alex_unavailable(seed: int) -> bool:
    """The seed rule behind M10's branch: odd seeds carry Alex's conflict."""
    return seed % 2 == 1


def task_m10_dinner_source_conflict(seed: int) -> "WorldState":
    """SOURCE-OF-TRUTH CONFLICT. The calendar always shows tomorrow evening
    FREE, so the structured signal always says 'go'. But Alex's email is the
    overriding source: on odd seeds Alex says they can't make it. The correct
    action is to order ONLY if calendar-free AND Alex-available; otherwise
    don't order and reply to reschedule. Trap (the failure we hunt): anchor on
    the free calendar, skim past Alex's email, order dinner + 'confirm' — which
    on conflict seeds is exactly wrong."""
    from server.apps.calendar.state import make_calendarstate
    from server.apps.mail.state import SEED_DATE
    world = _cross_app_world(seed, "M10/dinner_source_conflict", "hard")
    # Force the calendar FREE regardless of seed — for M10 the conflict comes
    # from the email, not the calendar (make_calendarstate busies odd seeds).
    world.calendar = make_calendarstate(0)
    # Replace the default Alex note with the branch-specific one (same subject
    # both ways so nothing leaks from the inbox list).
    m = world.mail
    body = _M10_ALEX_CONFLICT if _m10_alex_unavailable(seed) else _M10_ALEX_BENIGN
    alex_id = next((eid for eid, e in m.inbox.items()
                    if "alex@" in (e.sender or "")), None)
    if alex_id is not None:
        e = m.inbox[alex_id]
        e.subject = "Re: dinner tomorrow"
        e.body = body
        e.received_at = f"{SEED_DATE}T16:00:00"
        e.received_label = "4:00 PM"
        e.read = False
    return world


# M11 — long-horizon reconciliation over MANY confusable order emails. The
# agent must apply a TWO-condition filter (total > $100 AND not shipped) across
# 8 lookalike confirmations and reply-cancel EXACTLY the qualifying ones. Three
# trap types defeat a shortcut: shipped-but-expensive, cheap, and just-under
# $100. Qualifying set = {ORD-4471, ORD-4474, ORD-4476}; everything else is a
# skip. This targets compounding tracking errors: miss one, double-cancel, or
# cancel a trap. Fixed + deterministic (env-correctness); the difficulty is the
# 8-item filter + repeated cross-email actions, not seed noise.
_M11_ORDERS = [
    # (order_id, total, shipped, item)            -> qualifies?
    ("ORD-4471", 129.99, False, "Mechanical Keyboard"),          # YES
    ("ORD-4472",  45.00, False, "USB-C Cable (2-pack)"),         # no: cheap
    ("ORD-4473", 210.00, True,  "27\" Studio Monitor"),          # no: shipped (trap)
    ("ORD-4474", 156.50, False, "Anti-Fatigue Mat + Desk Lamp"), # YES
    ("ORD-4475",  89.99, False, "Bluetooth Speaker"),            # no: cheap
    ("ORD-4476", 340.00, False, "Standing Desk Converter"),      # YES
    ("ORD-4477",  99.99, False, "1080p Webcam"),                 # no: just under (trap)
    ("ORD-4478", 175.00, True,  "Noise-Cancelling Headphones"),  # no: shipped (trap)
]


def _m11_qualifies(total: float, shipped: bool) -> bool:
    """The M11 filter: over $100 AND not yet shipped."""
    return (total is not None) and total > 100.0 and not shipped


def task_m11_cancel_unshipped_over_100(seed: int) -> "WorldState":
    """LONG-HORIZON RECONCILIATION. Eight near-identical order-confirmation
    emails; cancel (reply) EXACTLY those over $100 AND not shipped. Traps:
    shipped-but-expensive, cheap, just-under-$100. Failure modes we hunt:
    missed a qualifying cancel (lost track over 8 items) or cancelled a
    non-qualifying one (skipped a condition)."""
    from server.apps.mail.state import Email, SEED_DATE
    world = _cross_app_world(seed, "M11/cancel_unshipped_over_100", "hard")
    m = world.mail
    for i, (oid, total, shipped, item) in enumerate(_M11_ORDERS):
        eid = m.new_id()
        status = "Shipped" if shipped else "Processing"
        hh = 8 + i  # distinct timestamps so the inbox order is stable
        m.inbox[eid] = Email(
            id=eid, sender="orders@shopgym.com", to=m.account_email,
            subject=f"Your ShopGym order {oid} is confirmed",
            body=(f"Thanks for your order!\n\n"
                  f"Order {oid}\n"
                  f"Item: {item}\n"
                  f"Order total: ${total:.2f}\n"
                  f"Status: {status}\n\n"
                  f"Questions? Just reply to this email."),
            received_at=f"{SEED_DATE}T{hh:02d}:00:00",
            received_label=f"{(hh-12) if hh>12 else hh}:00 {'PM' if hh>=12 else 'AM'}",
            read=False, labels=["orders"], order_id=oid, amount_total=total)
    return world


def task_m12_bulk_add_dense(seed: int) -> "GymState":
    """BUTTON-DENSITY / SMALL-TARGET stress (tim's hypothesis). Shop-only: the
    agent lands on the dense Quick Order grid (18 small tiles, generic "Add"
    buttons) and must add EXACTLY the mice + keyboards (8 of 18), skipping
    laptops/monitors/charger/smartwatch and the Magic Trackpad decoy. With the
    Add controls generically labelled, a Set-of-Mark agent can't disambiguate
    them from the manifest and must map Add->product visually -- which is where
    small, crowded targets are predicted to cause mis-adds."""
    return _base_state(seed, "M12/bulk_add_dense_grid", "hard", "M",
                       with_login=True)


# Per-task START PATH: where the harness drops the agent at episode start
# (default "/"). M12 starts on the dense grid so the small-target stress is the
# variable under test, not navigation.
START_PATHS = {
    "M12/bulk_add_dense_grid": "/bulk",
}


def task_m5_cheaper_mouse_from_deals(seed: int) -> "WorldState":
    """Comparison + salience trap. Two 'deal' emails name two DIFFERENT mice
    at two prices: the flashy 'FLASH SALE' email pushes the PRICIER gaming
    mouse ($20); the boring email has the genuinely cheaper ergonomic mouse
    ($16). The agent must read BOTH, compare, map the names to products, and
    order the cheaper one — resisting both the salient decoy and the
    'default' standard mouse. Reliably hard for a small VLM in pixel mode."""
    from server.apps.mail.state import Email, SEED_DATE
    world = _cross_app_world(seed, "M5/cheaper_mouse_from_deals", "hard")
    m = world.mail
    # Salient but PRICIER decoy — the gaming mouse at $20.
    eid = m.new_id()
    m.inbox[eid] = Email(
        id=eid, sender="deals@shopgym.com", to=m.account_email,
        subject="FLASH SALE: Gaming Mouse - today only!",
        body=("Our Studio Gaming Mouse is on a flash sale: $20.00 today "
              "only. Don't miss out!"),
        received_at=f"{SEED_DATE}T11:00:00", received_label="11:00 AM",
        read=False, labels=["mouse-deal"],
    )
    # Boring but CHEAPER (correct pick) — the ergonomic mouse at $16.
    eid = m.new_id()
    m.inbox[eid] = Email(
        id=eid, sender="deals@shopgym.com", to=m.account_email,
        subject="This week's picks",
        body=("A few staff picks this week - and the Ergonomic Mouse is "
              "marked down to $16.00, our lowest price yet."),
        received_at=f"{SEED_DATE}T11:05:00", received_label="11:05 AM",
        read=False, labels=["mouse-deal"],
    )
    return world


# Required-facts manifest: the facts the agent must carry ACROSS apps to
# succeed. Feeds the cross-app verifier and (Phase-1 commit 8) the failure-
# mode signature builder (facts observed vs facts required). Keyed by task_id.
REQUIRED_FACTS = {
    "M2/order_then_track_via_email": ["shop.order_id", "mail.tracking_url"],
    "M3/dinner_then_receipt":        ["food.order_id", "mail.receipt_total"],
    "M4/order_then_reply_total":     ["shop.order_total", "mail.confirmation_total"],
    "M5/cheaper_mouse_from_deals":   ["shop.ordered_mouse_id"],
    "M6/reorder_bigger_order":       ["mail.bigger_order_id", "shop.reordered_items"],
    "M7/dinner_and_host_gift":       ["food.eta", "shop.book_name"],
    "M8/spending_audit_branch":      ["mail.shop_orders_total", "mail.most_expensive_order_id"],
    "M9/calendar_gated_dinner":      ["calendar.evening_free", "food.eta", "calendar.user_event_created"],
    "M10/dinner_source_conflict":    ["calendar.evening_free", "mail.alex_available"],
    "M11/cancel_unshipped_over_100": ["mail.qualifying_orders"],
}


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

TASKS = {
    "A1/buy_wireless_mouse":     task_a1_buy_wireless_mouse,
    "A2/filter_laptop":          task_a2_filter_laptop,
    "A3/configure_bundle":       task_a3_configure_bundle,
    "A4/home_office_bundle":     task_a4_home_office_bundle,
    "B1/add_address":            task_b1_add_address,
    "B2/track_and_return":       task_b2_track_and_return,
    "B3/account_overhaul":       task_b3_account_overhaul,
    "B4/subscription_juggle":    task_b4_subscription_juggle,
    "C1/promo_partial":          task_c1_promo_partial,
    "C2/split_shipping_gift":    task_c2_split_shipping,
    "C3/subscription_loyalty":   task_c3_subscription,
    "C4/mega_checkout":          task_c4_mega_checkout,
    "D1/browse_audio_no_search":     task_d1_browse_audio,
    "D2/drill_electronics_keyboards": task_d2_drill_keyboards,
    "M2/order_then_track_via_email": task_m2_order_then_track,
    "M3/dinner_then_receipt":        task_m3_dinner_then_receipt,
    "M4/order_then_reply_total":     task_m4_order_then_reply_total,
    "M5/cheaper_mouse_from_deals":   task_m5_cheaper_mouse_from_deals,
    "M6/reorder_bigger_order":       task_m6_reorder_bigger_order,
    "M7/dinner_and_host_gift":       task_m7_dinner_and_host_gift,
    "M8/spending_audit_branch":      task_m8_spending_audit_branch,
    "M9/calendar_gated_dinner":      task_m9_calendar_gated_dinner,
    "M10/dinner_source_conflict":    task_m10_dinner_source_conflict,
    "M11/cancel_unshipped_over_100": task_m11_cancel_unshipped_over_100,
    "M12/bulk_add_dense_grid":       task_m12_bulk_add_dense,
}


def make_task(task_id: str, seed: int) -> "GymState | WorldState":
    """Returns a GymState for single-app tasks and a WorldState for the
    cross-app (category M) tasks. Callers that may receive either should
    branch on ``isinstance(result, WorldState)``."""
    if task_id not in TASKS:
        raise KeyError(f"unknown task {task_id!r}")
    return TASKS[task_id](seed)
