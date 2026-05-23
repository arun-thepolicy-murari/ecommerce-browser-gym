"""Hand-coded oracle agent — uses Playwright directly through BrowserCtx.

This is the gold trajectory for each task. It always scores 1.0 if the
verifier is correctly designed. Its purpose:
  1. Validate verifiers (oracle != 1.0 means the verifier has a bug)
  2. Produce gold trajectories for downstream SFT data
  3. Anchor the score range: the oracle is the ceiling

It's NOT an LLM. It's Python that knows exactly what each task wants.
"""

from __future__ import annotations

from harness.runner import BrowserCtx


# --------------------------------------------------------------------------- #
# Per-task solvers
# --------------------------------------------------------------------------- #

async def solve_a1_buy_wireless_mouse(ctx: BrowserCtx) -> None:
    await ctx.goto("/")
    await ctx.goto("/product/p_mouse_wireless",
                   reasoning="The target is 'Wireless Mouse' "
                             "(not 'Wireless Gaming Mouse').")
    await ctx.fill("input[data-test-id='input-qty']", "1")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_a2_filter_laptop(ctx: BrowserCtx) -> None:
    await ctx.goto("/search?category=electronics")
    await ctx.select("select[data-test-id='filter-category']", "electronics")
    await ctx.fill("input[data-test-id='filter-max-price']", "1000")
    await ctx.fill("input[data-test-id='filter-min-rating']", "4.5")
    await ctx.click("button[data-test-id='btn-apply-filters']")
    await ctx.click("a[data-test-id='card-product-p_laptop_studio']")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_a3_configure_bundle(ctx: BrowserCtx) -> None:
    # Add laptop with the right variant
    await ctx.goto("/product/p_laptop_studio")
    await ctx.select("select[data-test-id='select-variant']", "v_lt_32_1tb")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Add mouse
    await ctx.goto("/product/p_mouse_wireless")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Add keyboard
    await ctx.goto("/product/p_kb_mech")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Checkout
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_b1_add_address(ctx: BrowserCtx) -> None:
    await ctx.goto("/account/addresses")
    await ctx.fill("input[data-test-id='input-addr-label']", "Beach House")
    await ctx.fill("input[data-test-id='input-addr-full-name']",
                   "Alice Anderson")
    await ctx.fill("input[data-test-id='input-addr-line1']", "17 Ocean Drive")
    await ctx.fill("input[data-test-id='input-addr-city']", "Montauk")
    await ctx.fill("input[data-test-id='input-addr-state']", "NY")
    await ctx.fill("input[data-test-id='input-addr-zip']", "11954")
    await ctx.check("input[data-test-id='cb-set-default']")
    await ctx.click("button[data-test-id='btn-save-address']")


async def solve_b2_track_and_return(ctx: BrowserCtx) -> None:
    await ctx.goto("/account/orders")
    await ctx.click("a[data-test-id='link-order-ORD-EXISTING-1234']")
    # Open tracking modal page (in-place, since popup window won't be
    # navigable from here)
    await ctx.goto("/account/orders/ORD-EXISTING-1234/track",
                   reasoning="View tracking before initiating return.")
    await ctx.goto("/account/returns/new?order_id=ORD-EXISTING-1234")
    await ctx.check("input[data-test-id='cb-return-item-ln_mouse']")
    await ctx.select("select[data-test-id='select-return-reason']",
                     "defective")
    await ctx.click("input[data-test-id='radio-refund-original']")
    await ctx.click("button[data-test-id='btn-submit-return']")


async def solve_b3_account_overhaul(ctx: BrowserCtx) -> None:
    # 1. Set Work as default address
    await ctx.goto("/account/addresses")
    await ctx.click("button[data-test-id='btn-set-default-addr_work']")
    # 2. Add a backup payment method
    await ctx.goto("/account/payments")
    await ctx.fill("input[data-test-id='input-pay-nickname']", "Backup Card")
    await ctx.fill("input[data-test-id='input-pay-label']", "Backup Card")
    await ctx.fill("input[data-test-id='input-card-number']",
                   "4111111111111111")
    await ctx.fill("input[data-test-id='input-card-expires']", "12/29")
    await ctx.fill("input[data-test-id='input-card-cvv']", "123")
    await ctx.check("input[data-test-id='cb-set-default-pay']")
    await ctx.click("button[data-test-id='btn-save-payment']")
    # 3. Enable 2FA
    await ctx.goto("/account/security")
    await ctx.fill("input[data-test-id='input-2fa-code']", "123456")
    await ctx.click("button[data-test-id='btn-enable-2fa']")


async def solve_c1_promo_partial(ctx: BrowserCtx) -> None:
    # Add laptop + t-shirt
    await ctx.goto("/product/p_laptop_studio")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.goto("/product/p_clothing_tshirt")
    await ctx.select("select[data-test-id='select-variant']", "v_ts_m_blk")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Checkout
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    # Apply promo
    await ctx.fill("input[data-test-id='input-promo-code']", "TECH20")
    await ctx.click("button[data-test-id='btn-apply-promo']")
    # Place order
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_c2_split_shipping(ctx: BrowserCtx) -> None:
    # Add headphones
    await ctx.goto("/product/p_hp_studio")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Add mouse
    await ctx.goto("/product/p_mouse_wireless")
    await ctx.click("button[data-test-id='btn-add-to-cart']")

    # Go to cart and configure per-line options
    await ctx.goto("/cart")
    # Need to grab the line ids by reading the page. Easiest: backend
    # snapshot.
    snap = ctx.http.get(f"{ctx.server_url}/_harness/state").json()
    hp_line = next(
        l for l in snap["cart"]["items"]
        if l["product_id"] == "p_hp_studio"
    )
    mouse_line = next(
        l for l in snap["cart"]["items"]
        if l["product_id"] == "p_mouse_wireless"
    )
    # Configure headphone line: home + gift wrap + message
    await ctx.click(f"summary[data-test-id='toggle-line-options-{hp_line['id']}']")
    await ctx.check(f"input[data-test-id='cb-gift-wrap-{hp_line['id']}']")
    await ctx.fill(
        f"input[data-test-id='input-gift-message-{hp_line['id']}']",
        "Happy birthday",
    )
    await ctx.select(
        f"select[data-test-id='select-ship-address-{hp_line['id']}']",
        "addr_home",
    )
    await ctx.click(f"button[data-test-id='btn-save-line-{hp_line['id']}']")
    # Configure mouse line: work, no gift wrap
    await ctx.click(f"summary[data-test-id='toggle-line-options-{mouse_line['id']}']")
    await ctx.select(
        f"select[data-test-id='select-ship-address-{mouse_line['id']}']",
        "addr_work",
    )
    await ctx.click(f"button[data-test-id='btn-save-line-{mouse_line['id']}']")
    # Place order
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_c3_subscription(ctx: BrowserCtx) -> None:
    await ctx.goto("/product/p_pet_food")
    # The Subscribe & Save panel is collapsed behind an Alpine.js toggle
    # (x-show="open"). Click the toggle to reveal the form before filling.
    await ctx.click("button[data-test-id='btn-toggle-subscribe']")
    await ctx.select("select[data-test-id='select-cadence']", "weekly")
    await ctx.fill("input[data-test-id='input-deliveries']", "4")
    await ctx.select("select[data-test-id='select-sub-address']", "addr_home")
    await ctx.select("select[data-test-id='select-sub-payment']", "pay_visa")
    await ctx.click("button[data-test-id='btn-create-subscription']")


# --------------------------------------------------------------------------- #
# Very-hard tasks (A4, B4, C4) — added May 2026 alongside the new tasks.
# These exist primarily as verifier sanity gates: if the oracle scores < 1.0,
# the task is unsolvable as designed.
# --------------------------------------------------------------------------- #

async def solve_a4_home_office_bundle(ctx: BrowserCtx) -> None:
    """4-item electronics bundle under $550 → Work + PayPal.

    Note: per-line address is set in the cart via the line-options
    `<details>` toggle (mirrors C2's pattern). Final payment is
    selected at the /checkout/review step's dropdown.
    """
    # Add the 4 required items
    for pid in ("p_monitor_27", "p_kb_mech",
                "p_mouse_ergonomic", "p_charger"):
        await ctx.goto(f"/product/{pid}")
        await ctx.click("button[data-test-id='btn-add-to-cart']")

    # Per-line: ship all four to Work
    await ctx.goto("/cart")
    snap = ctx.http.get(f"{ctx.server_url}/_harness/state").json()
    for line in snap["cart"]["items"]:
        lid = line["id"]
        await ctx.click(
            f"summary[data-test-id='toggle-line-options-{lid}']"
        )
        await ctx.select(
            f"select[data-test-id='select-ship-address-{lid}']",
            "addr_work",
        )
        await ctx.click(f"button[data-test-id='btn-save-line-{lid}']")

    # Through checkout → pay with PayPal at the review step
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.select(
        "select[data-test-id='select-final-payment']", "pay_paypal",
    )
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_b4_subscription_juggle(ctx: BrowserCtx) -> None:
    """Cancel dogfood sub + create treats sub + enable 2FA + partial return."""
    # 1. Cancel existing Premium Dog Food subscription
    await ctx.goto("/account/subscriptions")
    await ctx.click(
        "button[data-test-id='btn-cancel-sub-sub_existing_dogfood']",
        reasoning="Cancel the pre-seeded active dog food subscription.",
    )

    # 2. Create NEW subscription for Dog TREATS — biweekly, 6, Work, PayPal
    await ctx.goto("/product/p_pet_treats")
    # The subscribe form is collapsed behind a toggle button
    await ctx.click("button[data-test-id='btn-toggle-subscribe']")
    await ctx.select("select[data-test-id='select-cadence']", "biweekly")
    await ctx.fill("input[data-test-id='input-deliveries']", "6")
    await ctx.select("select[data-test-id='select-sub-address']", "addr_work")
    await ctx.select("select[data-test-id='select-sub-payment']", "pay_paypal")
    await ctx.click("button[data-test-id='btn-create-subscription']")

    # 3. Enable 2FA
    await ctx.goto("/account/security")
    await ctx.fill("input[data-test-id='input-2fa-code']", "123456")
    await ctx.click("button[data-test-id='btn-enable-2fa']")

    # 4. Initiate return on ORD-B4-9999 for Bluetooth Speaker only
    await ctx.goto("/account/returns/new?order_id=ORD-B4-9999")
    await ctx.check("input[data-test-id='cb-return-item-ln_speaker']")
    await ctx.select("select[data-test-id='select-return-reason']",
                     "changed_mind")
    await ctx.click("input[data-test-id='radio-refund-credit']")
    await ctx.click("button[data-test-id='btn-submit-return']")


async def solve_c4_mega_checkout(ctx: BrowserCtx) -> None:
    """3 items × 3 shipping configs + TECH20 promo on laptop only + Visa."""
    # Add Studio Laptop 14 (NOT the Pro)
    await ctx.goto("/product/p_laptop_studio")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Add Cotton T-Shirt in size M Black
    await ctx.goto("/product/p_clothing_tshirt")
    await ctx.select("select[data-test-id='select-variant']", "v_ts_m_blk")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    # Add standard Wireless Mouse (NOT ergonomic / gaming)
    await ctx.goto("/product/p_mouse_wireless")
    await ctx.click("button[data-test-id='btn-add-to-cart']")

    # Configure per-line shipping in the cart
    await ctx.goto("/cart")
    snap = ctx.http.get(f"{ctx.server_url}/_harness/state").json()
    laptop_line = next(
        l for l in snap["cart"]["items"]
        if l["product_id"] == "p_laptop_studio"
    )
    tshirt_line = next(
        l for l in snap["cart"]["items"]
        if l["product_id"] == "p_clothing_tshirt"
    )
    mouse_line = next(
        l for l in snap["cart"]["items"]
        if l["product_id"] == "p_mouse_wireless"
    )
    # Laptop → Work (no gift wrap)
    await ctx.click(
        f"summary[data-test-id='toggle-line-options-{laptop_line['id']}']"
    )
    await ctx.select(
        f"select[data-test-id='select-ship-address-{laptop_line['id']}']",
        "addr_work",
    )
    await ctx.click(f"button[data-test-id='btn-save-line-{laptop_line['id']}']")
    # T-shirt → Home, gift wrap, "Happy Birthday Mom!"
    await ctx.click(
        f"summary[data-test-id='toggle-line-options-{tshirt_line['id']}']"
    )
    await ctx.check(f"input[data-test-id='cb-gift-wrap-{tshirt_line['id']}']")
    await ctx.fill(
        f"input[data-test-id='input-gift-message-{tshirt_line['id']}']",
        "Happy Birthday Mom!",
    )
    await ctx.select(
        f"select[data-test-id='select-ship-address-{tshirt_line['id']}']",
        "addr_home",
    )
    await ctx.click(f"button[data-test-id='btn-save-line-{tshirt_line['id']}']")
    # Mouse → Home, no gift wrap
    await ctx.click(
        f"summary[data-test-id='toggle-line-options-{mouse_line['id']}']"
    )
    await ctx.select(
        f"select[data-test-id='select-ship-address-{mouse_line['id']}']",
        "addr_home",
    )
    await ctx.click(f"button[data-test-id='btn-save-line-{mouse_line['id']}']")

    # Proceed → checkout → review with TECH20 promo + Visa
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.fill("input[data-test-id='input-promo-code']", "TECH20")
    await ctx.click("button[data-test-id='btn-apply-promo']")
    await ctx.select(
        "select[data-test-id='select-final-payment']", "pay_visa",
    )
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_d1_browse_audio(ctx: BrowserCtx) -> None:
    # Browse the taxonomy (NO search bar): Audio category -> headphones
    # subcategory -> a 4.5+ pair. Each goto logs view_category /
    # view_subcategory, which the verifier requires.
    await ctx.goto("/category/audio",
                   reasoning="Browse the Audio department instead of searching.")
    await ctx.goto("/category/audio?sub=headphones",
                   reasoning="Drill into the headphones subcategory.")
    await ctx.click("a[data-test-id='card-product-p_hp_premium']")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_d2_drill_keyboards(ctx: BrowserCtx) -> None:
    # Electronics -> keyboards subcategory -> the mechanical one (not the
    # membrane). Browse, don't search.
    await ctx.goto("/category/electronics",
                   reasoning="Browse the Electronics department.")
    await ctx.goto("/category/electronics?sub=keyboards",
                   reasoning="Drill into the keyboards subcategory.")
    await ctx.click("a[data-test-id='card-product-p_kb_mech']")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


# --------------------------------------------------------------------------- #
# Category M: cross-app journeys (Shop / Mail / Food in one browser).
# The oracle navigates across apps in a single tab; the multi-tab path is
# the richer option the LLM/pixel agents get. These are the verifier sanity
# gates for the cross-app tasks.
# --------------------------------------------------------------------------- #

async def solve_m2_order_then_track(ctx: BrowserCtx) -> None:
    """Order the standard wireless mouse, then find the confirmation email
    and follow ITS tracking link.

    Demonstrates TRUE multi-tab the way a person works: the Shop stays in
    tab 0, Mail opens in a SECOND tab to read the confirmation, then we flip
    BACK to the Shop tab to check tracking — carrying the order id across the
    tab switch (the exact hop weak agents fumble)."""
    # Tab 0 (Shop): order the standard wireless mouse (not gaming/ergonomic).
    await ctx.goto("/product/p_mouse_wireless",
                   reasoning="The standard wireless mouse, not the gaming one.")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")
    # Open Mail in a SECOND tab (the shop tab stays exactly where it is).
    await ctx.open_tab("/mail",
                       reasoning="Open Mail in a new tab to find the order confirmation.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    conf = next(e for e in world["mail"]["inbox"].values()
                if e.get("tracking_url"))
    await ctx.goto(f"/mail/message/{conf['id']}",
                   reasoning="Open the confirmation email in the Mail tab.")
    # Flip BACK to the Shop tab and follow the tracking link there.
    await ctx.switch_tab(0,
                         reasoning="Switch back to the Shop tab to check tracking.")
    await ctx.goto(conf["tracking_url"],
                   reasoning="Follow the tracking link from the email.")


async def solve_m3_dinner_then_receipt(ctx: BrowserCtx) -> None:
    """Order dinner from the Food app, then open the receipt email."""
    await ctx.goto("/food", reasoning="Open the food-delivery app.")
    await ctx.goto("/food/restaurant/r_sushi", reasoning="Pick a restaurant.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    # Switch to Mail and open the receipt (the only inbox mail labelled
    # 'receipts').
    await ctx.goto("/mail", reasoning="Check email for the receipt.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    receipt = next(e for e in world["mail"]["inbox"].values()
                   if "receipts" in (e.get("labels") or []))
    await ctx.goto(f"/mail/message/{receipt['id']}",
                   reasoning="Open the receipt email to confirm the order.")


async def solve_m4_order_then_reply_total(ctx: BrowserCtx) -> None:
    """Order the mouse, open the confirmation email, and reply with the
    EXACT charged total (subtotal + tax + shipping) read from the order."""
    # Tab 0: order the standard wireless mouse.
    await ctx.goto("/product/p_mouse_wireless",
                   reasoning="The standard wireless mouse, not the gaming one.")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")
    # Read the CHARGED total + confirmation email from the world.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    conf = next(e for e in world["mail"]["inbox"].values()
                if e.get("tracking_url"))
    total = world["shop"]["orders"][conf["order_id"]]["total"]
    # Open Mail in a second tab, open the confirmation, reply with the total.
    await ctx.open_tab("/mail",
                       reasoning="Open Mail in a new tab to read the confirmation.")
    await ctx.goto(f"/mail/message/{conf['id']}",
                   reasoning="Open the confirmation email to read the charged total.")
    await ctx.click("a[data-test-id='btn-reply']",
                    reasoning="Reply to the confirmation email.")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        f"The exact total charged was ${total:.2f}, including tax and shipping.",
    )
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m5_cheaper_mouse_from_deals(ctx: BrowserCtx) -> None:
    """Read BOTH mouse-deal emails, then order the genuinely cheaper one
    (ergonomic $16 < gaming $20) — resisting the flashy gaming decoy."""
    # Open Mail in a second tab and read both deal emails.
    await ctx.open_tab("/mail", reasoning="Read the two mouse deals.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    deals = [e for e in world["mail"]["inbox"].values()
             if "mouse-deal" in (e.get("labels") or [])]
    for e in deals:
        await ctx.goto(f"/mail/message/{e['id']}",
                       reasoning="Read this deal to compare prices.")
    # Ergonomic ($16) is cheaper than Gaming ($20) -> order the ergonomic.
    await ctx.switch_tab(0,
                         reasoning="Back to the Shop to order the cheaper mouse.")
    await ctx.goto("/product/p_mouse_ergonomic",
                   reasoning="The ergonomic mouse is the cheaper deal.")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_m6_reorder_bigger_order(ctx: BrowserCtx) -> None:
    """Compare the two past-order confirmation emails, reorder the BIGGER
    order's in-stock items (laptop + keyboard; charger is OOS), then reply
    to that order's email listing what was reordered."""
    await ctx.open_tab("/mail", reasoning="Find the two past order confirmations.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    confs = {e["order_id"]: e for e in world["mail"]["inbox"].values()
             if (e.get("order_id") or "").startswith("ORD-PAST")}
    for e in confs.values():                       # open both to read the totals
        await ctx.goto(f"/mail/message/{e['id']}",
                       reasoning="Read this confirmation's total.")
    big = max(confs.values(), key=lambda e: e.get("amount_total") or 0)
    # Reorder the bigger order's IN-STOCK items (the charger is out of stock).
    await ctx.switch_tab(0, reasoning="Back to the shop to reorder the bigger order.")
    for pid in ("p_laptop_studio", "p_kb_mech"):
        await ctx.goto(f"/product/{pid}",
                       reasoning="Reorder this item from the bigger order.")
        await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")
    # Reply to the bigger order's confirmation listing what we reordered.
    await ctx.switch_tab(1, reasoning="Back to Mail to reply to the bigger order.")
    await ctx.goto(f"/mail/message/{big['id']}",
                   reasoning="Open the bigger order's confirmation to reply.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        "I reordered the Studio Laptop 14 and the Mechanical Keyboard. The "
        "USB-C charger was out of stock, so I skipped it.",
    )
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m7_dinner_and_host_gift(ctx: BrowserCtx) -> None:
    """Order food under $35, buy the qualifying host-gift book (>=4.5 stars,
    under $20), then reply to Alex with the food ETA + the book name."""
    # 1) Food under $35.
    await ctx.open_tab("/food", reasoning="Order dinner from the food app.")
    await ctx.goto("/food/restaurant/r_sushi", reasoning="Pick a restaurant.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    eta = next(iter(world["food"]["orders"].values()))["eta_label"]
    # 2) The qualifying book: Project Hail Mary (4.7 stars, $16.50).
    await ctx.switch_tab(0, reasoning="Back to the shop for the host gift.")
    await ctx.goto("/product/p_book_sci_fi",
                   reasoning="A book rated 4.5+ and under $20.")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")
    # 3) Reply to Alex with the ETA + the book.
    await ctx.switch_tab(1, reasoning="Back to Mail to reply to Alex.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    alex = next(e for e in world["mail"]["inbox"].values()
                if "alex@" in (e.get("sender") or ""))
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Open Alex's dinner email to reply.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        f"All set for tonight! Dinner should arrive around {eta}, and I "
        f"picked up Project Hail Mary as the host gift.",
    )
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m8_spending_audit_branch(ctx: BrowserCtx) -> None:
    """Sum the 3 past order totals (> $1,000 -> overspend branch): buy
    NOTHING new, and reply to the MOST EXPENSIVE order asking to cancel it."""
    await ctx.open_tab("/mail", reasoning="Find the order confirmations.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    confs = {e["order_id"]: e for e in world["mail"]["inbox"].values()
             if (e.get("order_id") or "").startswith("ORD-P")}
    for e in confs.values():                       # read all three totals
        await ctx.goto(f"/mail/message/{e['id']}",
                       reasoning="Read this order's total.")
    total = sum((e.get("amount_total") or 0) for e in confs.values())
    big = max(confs.values(), key=lambda e: e.get("amount_total") or 0)
    # total (~$1,319.92) > $1,000 -> overspend branch: cancel the priciest,
    # buy nothing new.
    await ctx.goto(f"/mail/message/{big['id']}",
                   reasoning="Open the most expensive order to reply.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        f"Please cancel order {big['order_id']} - my recent orders total "
        f"over $1,000 and I've been overspending this month. Thank you.",
    )
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m9_calendar_gated_dinner(ctx: BrowserCtx) -> None:
    """Free/busy-GATED. Read the calendar, then branch:
      FREE  -> order food + add a delivery event + email Alex to confirm.
      BUSY  -> don't order; email Alex to propose Thursday."""
    # Check the calendar first — the gate.
    await ctx.goto("/calendar", reasoning="Check whether tomorrow evening is free.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    cal = world.get("calendar") or {}
    tomorrow = cal.get("tomorrow")
    # Tomorrow-evening (18:00-23:00) overlap, mirroring CalendarState.is_free.
    evening_busy = any(
        ev.get("day") == tomorrow and ev.get("start", "") < "23:00"
        and "18:00" < ev.get("end", "")
        for ev in (cal.get("events") or {}).values())

    alex = next(e for e in world["mail"]["inbox"].values()
                if "alex@" in (e.get("sender") or ""))

    if evening_busy:
        # BUSY branch: do NOT order, propose Thursday.
        await ctx.goto(f"/mail/message/{alex['id']}",
                       reasoning="Tomorrow evening is busy - ask Alex about Thursday.")
        await ctx.click("a[data-test-id='btn-reply']")
        await ctx.fill(
            "textarea[data-test-id='input-compose-body']",
            "I'm tied up tomorrow evening - could we move dinner to Thursday "
            "instead? Let me know what works.",
        )
        await ctx.click("button[data-test-id='btn-send']")
        return

    # FREE branch: order dinner.
    await ctx.goto("/food/restaurant/r_sushi",
                   reasoning="Calendar is free tomorrow evening - order dinner.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    eta = next(iter(world["food"]["orders"].values()))["eta_label"]
    # Add a calendar event for the delivery (day defaults to tomorrow).
    await ctx.goto("/calendar/new", reasoning="Add the delivery to the calendar.")
    await ctx.fill("input[data-test-id='input-event-title']",
                   f"Dinner delivery ~{eta}")
    await ctx.click("button[data-test-id='btn-save-event']")
    # Email Alex to confirm (free branch -> confirm, not propose Thursday).
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Reply to Alex to confirm tomorrow's dinner.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        f"Confirmed - we're on for dinner tomorrow evening, arriving around "
        f"{eta}. See you then!",
    )
    await ctx.click("button[data-test-id='btn-send']")


SOLVERS = {
    "A1/buy_wireless_mouse":     solve_a1_buy_wireless_mouse,
    "A2/filter_laptop":          solve_a2_filter_laptop,
    "A3/configure_bundle":       solve_a3_configure_bundle,
    "A4/home_office_bundle":     solve_a4_home_office_bundle,
    "B1/add_address":            solve_b1_add_address,
    "B2/track_and_return":       solve_b2_track_and_return,
    "B3/account_overhaul":       solve_b3_account_overhaul,
    "B4/subscription_juggle":    solve_b4_subscription_juggle,
    "C1/promo_partial":          solve_c1_promo_partial,
    "C2/split_shipping_gift":    solve_c2_split_shipping,
    "C3/subscription_loyalty":   solve_c3_subscription,
    "C4/mega_checkout":          solve_c4_mega_checkout,
    "D1/browse_audio_no_search":     solve_d1_browse_audio,
    "D2/drill_electronics_keyboards": solve_d2_drill_keyboards,
    "M2/order_then_track_via_email": solve_m2_order_then_track,
    "M3/dinner_then_receipt":        solve_m3_dinner_then_receipt,
    "M4/order_then_reply_total":     solve_m4_order_then_reply_total,
    "M5/cheaper_mouse_from_deals":   solve_m5_cheaper_mouse_from_deals,
    "M6/reorder_bigger_order":       solve_m6_reorder_bigger_order,
    "M7/dinner_and_host_gift":       solve_m7_dinner_and_host_gift,
    "M8/spending_audit_branch":      solve_m8_spending_audit_branch,
    "M9/calendar_gated_dinner":      solve_m9_calendar_gated_dinner,
}
