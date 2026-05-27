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


async def solve_m10_dinner_source_conflict(ctx: BrowserCtx) -> None:
    """Reconcile the two sources. Calendar is always free, so the answer
    hinges on Alex's email: if Alex can't make it, don't order and reply to
    reschedule; otherwise order dinner and reply to confirm."""
    # Read both sources before acting.
    await ctx.goto("/calendar", reasoning="Check whether tomorrow evening is free.")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    alex = next(e for e in world["mail"]["inbox"].values()
                if "alex@" in (e.get("sender") or ""))
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Read Alex's latest email for any change of plans.")
    body = (alex.get("body") or "").lower()
    conflict = any(w in body for w in
                   ("another day", "can't make", "won't land",
                    "can't do dinner", "reschedule"))

    if conflict:
        # Alex is unavailable -> do NOT order; reply to reschedule.
        await ctx.click("a[data-test-id='btn-reply']")
        await ctx.fill(
            "textarea[data-test-id='input-compose-body']",
            "No problem at all - let's find another day. Would Thursday "
            "evening work for you instead?",
        )
        await ctx.click("button[data-test-id='btn-send']")
        return

    # Both clear -> order dinner, then confirm with Alex.
    await ctx.goto("/food/restaurant/r_sushi",
                   reasoning="Calendar free + Alex available - order dinner.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Reply to Alex to confirm tomorrow's dinner.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        "Confirmed - dinner tomorrow evening it is. See you then!",
    )
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m11_cancel_unshipped_over_100(ctx: BrowserCtx) -> None:
    """Reconcile 8 order emails: reply-cancel exactly those over $100 AND not
    shipped. Reads each order's total + status from the world, filters, and
    replies to every qualifying one (and only those)."""
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    inbox = (world.get("mail") or {}).get("inbox") or {}
    # Build the qualifying list from the seeded emails.
    qualifying = []
    for e in inbox.values():
        oid = e.get("order_id") or ""
        if not oid.startswith("ORD-"):
            continue
        total = e.get("amount_total") or 0.0
        shipped = "status: shipped" in (e.get("body") or "").lower()
        if total > 100.0 and not shipped:
            qualifying.append((e["id"], oid))
    # Reply-cancel each qualifying order (and nothing else).
    for eid, oid in qualifying:
        await ctx.goto(f"/mail/message/{eid}",
                       reasoning=f"Open order {oid} (over $100, not shipped).")
        await ctx.click("a[data-test-id='btn-reply']")
        await ctx.fill(
            "textarea[data-test-id='input-compose-body']",
            f"Please cancel order {oid}. It hasn't shipped yet and I'd like "
            f"to cancel it. Thank you.",
        )
        await ctx.click("button[data-test-id='btn-send']")


async def solve_m12_bulk_add_dense(ctx: BrowserCtx) -> None:
    """On the dense Quick Order grid, add exactly the mice + keyboards via
    their quick-add buttons. Targets by data-test-id, so it's precise where a
    visual agent must disambiguate crowded generic 'Add' buttons. The 8 ids
    are the electronics whose NAME contains mouse/keyboard (matches the
    verifier's qualifying set); the Magic Trackpad is intentionally excluded."""
    await ctx.goto("/bulk", reasoning="Open the Quick Order grid.")
    qualifying = [
        "p_mouse_wireless", "p_mouse_gaming", "p_mouse_ergonomic", "p_mouse_mini",
        "p_kb_mech", "p_kb_wireless", "p_kb_mini", "p_kb_membrane",
    ]
    for pid in qualifying:
        await ctx.click(f"button[data-test-id='btn-quickadd-{pid}']",
                        reasoning=f"Add {pid} (a mouse or keyboard).")


async def solve_m13_order_cleanup_audit(ctx: BrowserCtx) -> None:
    """Reconcile 14 order emails: reply-cancel exactly those that are unshipped
    AND CHARGED > $50 (amount_total = charged, NOT the subtotal) AND not the
    gift. Reads each order's charged/status/gift from the world and replies to
    every qualifying one (and only those)."""
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    inbox = (world.get("mail") or {}).get("inbox") or {}
    qualifying = []
    for e in inbox.values():
        oid = e.get("order_id") or ""
        if not oid.startswith("ORD-"):
            continue
        charged = e.get("amount_total") or 0.0
        body = (e.get("body") or "").lower()
        shipped = "status: shipped" in body
        is_gift = "gift note" in body
        if charged > 50.0 and not shipped and not is_gift:
            qualifying.append((e["id"], oid))
    for eid, oid in qualifying:
        await ctx.goto(f"/mail/message/{eid}",
                       reasoning=f"Open {oid} (charged > $50, unshipped, not a gift).")
        await ctx.click("a[data-test-id='btn-reply']")
        await ctx.fill(
            "textarea[data-test-id='input-compose-body']",
            f"Please cancel order {oid} — I was charged over $50 and it hasn't "
            f"shipped. Thank you.",
        )
        await ctx.click("button[data-test-id='btn-send']")


async def solve_m14_return_then_refund(ctx: BrowserCtx) -> None:
    """Read the RMA from the support email, file the mouse-only return (RMA in
    notes), WAIT for the async refund email (arrives 3 steps after filing),
    open it, and reply confirming the exact refund."""
    import re
    # 1) Read the return-authorization code from the support email.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    support = next(e for e in world["mail"]["inbox"].values()
                   if "support@" in (e.get("sender") or "").lower())
    m = re.search(r"RMA-\d+", support.get("body", ""))
    rma = m.group(0) if m else ""
    # 2) File the return for the mouse only, RMA in notes, refund to original.
    await ctx.goto("/account/returns/new?order_id=ORD-RET-1",
                   reasoning="Open the return form for the defective mouse.")
    await ctx.check("input[data-test-id='cb-return-item-ln_mouse']")
    await ctx.select("select[data-test-id='select-return-reason']", "defective")
    await ctx.click("input[data-test-id='radio-refund-original']")
    await ctx.fill("textarea[data-test-id='textarea-return-notes']",
                   f"Return authorization: {rma}")
    await ctx.click("button[data-test-id='btn-submit-return']")
    # 3) Wait for the async refund-approval email (fires 3 steps after filing).
    for _ in range(4):
        await ctx.wait(reasoning="Wait for the refund-approval email to arrive.")
    # 4) Read the exact refund amount off the email, then reply confirming it.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    refund_email = next(
        e for e in world["mail"]["inbox"].values()
        if "refunds@" in (e.get("sender") or "").lower())
    amt = refund_email["amount_total"]
    await ctx.goto(f"/mail/message/{refund_email['id']}",
                   reasoning="Open the refund-approval email.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill(
        "textarea[data-test-id='input-compose-body']",
        f"Confirmed — the refund of ${amt:.2f} is correct, and the mouse is on "
        f"its way back to you. Thanks!")
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m15_inbox_price_watch(ctx: BrowserCtx) -> None:
    """Wait on the inbox for the price-drop alert (fires at step 4), read which
    mouse + new price it names, then buy exactly that mouse at the new price."""
    # 1) Wait for the async alert to land (poll the world; the absolute event
    #    fires once the clock reaches step 4 — each wait ticks it forward).
    pid = None
    for _ in range(8):
        world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
        alert = next(
            (e for e in world["mail"]["inbox"].values()
             if "price-drop" in (e.get("labels") or [])), None)
        if alert is not None:
            pid = alert["product_id"]
            await ctx.goto(f"/mail/message/{alert['id']}",
                           reasoning="Open the price-drop alert to read the "
                                     "mouse and its new price.")
            break
        await ctx.wait(reasoning="Wait for the price-drop alert to arrive.")
    # 2) Buy exactly the alerted mouse — its price is now the dropped one.
    await ctx.goto(f"/product/{pid}",
                   reasoning="Buy the alerted mouse at the new (dropped) price.")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")
    await ctx.click("a[data-test-id='btn-continue-payment']")
    await ctx.click("a[data-test-id='btn-continue-review']")
    await ctx.click("button[data-test-id='btn-place-order']")


async def solve_m16_coordinated_dinner_delay(ctx: BrowserCtx) -> None:
    """Order dinner, add a reminder + tell the guest at the first ETA; when the
    async DeliveryDelayed notice arrives, MOVE the reminder to the new ETA
    (leaving exactly one event) and tell the guest the new time."""
    # 1) Order the sushi (its ETA is 7:00 PM).
    await ctx.goto("/food/restaurant/r_sushi", reasoning="Order tonight's dinner.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    # 2) Add the delivery reminder at the FIRST ETA (7:00 PM -> 19:00).
    await ctx.goto("/calendar/new",
                   reasoning="Add a reminder for the delivery ETA.")
    await ctx.fill("input[data-test-id='input-event-title']", "Dinner delivery")
    await ctx.fill("input[data-test-id='input-event-start']", "19:00")
    await ctx.fill("input[data-test-id='input-event-end']", "19:30")
    await ctx.click("button[data-test-id='btn-save-event']")
    # 3) Tell Alex the first time.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    alex = next(e for e in world["mail"]["inbox"].values()
                if "alex@" in (e.get("sender") or ""))
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Let Alex know the delivery time.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill("textarea[data-test-id='input-compose-body']",
                   "Dinner's on the way — should arrive around 7:00 PM!")
    await ctx.click("button[data-test-id='btn-send']")
    # 4) Wait for the async delay notice (fires a few steps after the order).
    notice = None
    for _ in range(8):
        world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
        notice = next((e for e in world["mail"]["inbox"].values()
                       if "delivery" in (e.get("labels") or [])), None)
        if notice is not None:
            break
        await ctx.wait(reasoning="Wait for any delivery-delay notice.")
    # 5) Read the delay notice (new ETA 8:00 PM).
    await ctx.goto(f"/mail/message/{notice['id']}",
                   reasoning="Read the delay notice for the new ETA.")
    # 6) MOVE the existing reminder to the new ETA (NOT a second event).
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    ev_id = next(eid for eid, ev in world["calendar"]["events"].items()
                 if ev.get("source") == "user")
    await ctx.goto(f"/calendar/edit/{ev_id}",
                   reasoning="Push the existing reminder to the new ETA.")
    await ctx.fill("input[data-test-id='input-edit-start']", "20:00")
    await ctx.fill("input[data-test-id='input-edit-end']", "20:30")
    await ctx.click("button[data-test-id='btn-update-event']")
    # 7) Tell Alex the NEW time.
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Update Alex with the new delivery time.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill("textarea[data-test-id='input-compose-body']",
                   "Quick update — the kitchen pushed it back, so it'll now "
                   "arrive around 8:00 PM instead.")
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m20_errand_run(ctx: BrowserCtx) -> None:
    """Complete all three bundled sub-goals: (1) buy keyboard+mouse on ValueMart
    with VALUE10 under $125, (2) order Sakura Sushi + add a calendar reminder,
    (3) reply to Alex with the exact gear total."""
    # 1) Gear on ValueMart with VALUE10.
    await ctx.goto("/market/product/vm_kb_mech", reasoning="ValueMart keyboard.")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/product/vm_mouse_wireless")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/cart")
    await ctx.fill("input[data-test-id='market-input-coupon']", "VALUE10")
    await ctx.click("button[data-test-id='market-btn-apply-coupon']")
    await ctx.click("button[data-test-id='market-btn-place-order']")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    gear = next(o for o in world["market"]["orders"].values()
                if o.get("coupon_code") == "VALUE10")
    total = gear["total"]
    # 2) Dinner from Sakura Sushi + a calendar reminder.
    await ctx.goto("/food/restaurant/r_sushi", reasoning="Order tonight's dinner.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    await ctx.goto("/calendar/new", reasoning="Add a reminder for the delivery.")
    await ctx.fill("input[data-test-id='input-event-title']", "Sushi delivery")
    await ctx.click("button[data-test-id='btn-save-event']")
    # 3) Reply to Alex with the EXACT gear total.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    alex = next(e for e in world["mail"]["inbox"].values()
                if "alex@" in (e.get("sender") or "").lower()
                and "keyboard" in (e.get("subject") or "").lower())
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Reply to Alex with the gear cost.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill("textarea[data-test-id='input-compose-body']",
                   f"The keyboard and mouse came to ${total:.2f} total at "
                   f"ValueMart. Hope that helps!")
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m21_async_errand_run(ctx: BrowserCtx) -> None:
    """Gold trajectory for the combined juggle × async-flip task. Crucially,
    WAIT for the flash-sale flip BEFORE buying gear (so we apply the post-flip
    VALUEMART20, not the stale VALUE10), then complete the other three errands
    and reply to Alex with the EXACT post-flip total."""
    import re
    # 1) Watch the inbox for the mid-task flash-sale coupon before buying.
    code = "VALUEMART20"
    for _ in range(8):
        world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
        flip = next((e for e in world["mail"]["inbox"].values()
                     if "coupon-flip" in (e.get("labels") or [])), None)
        if flip is not None:
            m = re.search(r"VALUEMART\d+", flip.get("body", "") or "")
            code = m.group(0) if m else code
            await ctx.goto(f"/mail/message/{flip['id']}",
                           reasoning="A bigger ValueMart coupon arrived — read it.")
            break
        await ctx.wait(reasoning="Watch the inbox for the best live coupon "
                                 "before checking out.")
    # 2) Buy keyboard + mouse on ValueMart with the post-flip coupon.
    await ctx.goto("/market/product/vm_kb_mech",
                   reasoning="ValueMart keyboard.")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/product/vm_mouse_wireless")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/cart")
    await ctx.fill("input[data-test-id='market-input-coupon']", code)
    await ctx.click("button[data-test-id='market-btn-apply-coupon']")
    await ctx.click("button[data-test-id='market-btn-place-order']")
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    gear = next(o for o in world["market"]["orders"].values()
                if o.get("coupon_code") == code)
    total = gear["total"]
    # 3) Dinner from Sakura Sushi + a calendar reminder.
    await ctx.goto("/food/restaurant/r_sushi",
                   reasoning="Order tonight's dinner.")
    await ctx.click("button[data-test-id='btn-add-d_salmon_roll']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    await ctx.goto("/calendar/new",
                   reasoning="Add a reminder for the delivery.")
    await ctx.fill("input[data-test-id='input-event-title']", "Sushi delivery")
    await ctx.click("button[data-test-id='btn-save-event']")
    # 4) Reply to Alex with the EXACT post-flip total.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    alex = next(e for e in world["mail"]["inbox"].values()
                if "alex@" in (e.get("sender") or "").lower()
                and "keyboard" in (e.get("subject") or "").lower())
    await ctx.goto(f"/mail/message/{alex['id']}",
                   reasoning="Reply to Alex with the gear cost.")
    await ctx.click("a[data-test-id='btn-reply']")
    await ctx.fill("textarea[data-test-id='input-compose-body']",
                   f"The keyboard and mouse came to ${total:.2f} total at "
                   f"ValueMart. Hope that helps!")
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m22_async_calendar_cascade(ctx: BrowserCtx) -> None:
    """Gold trajectory for the destructive async overwrite. Order the coffee,
    WAIT for the manager's change email, then: move the 1:1 up to 2 PM, DELETE
    the cancelled Team Sync (the step agents skip), and reply to Priya with the
    new time."""
    # 1) Concurrent juggling load: order the coffee from Bean There Cafe.
    await ctx.goto("/food/restaurant/r_bean", reasoning="Order the latte.")
    await ctx.click("button[data-test-id='btn-add-d_latte']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    # 2) Watch the inbox for the manager's schedule-change email.
    for _ in range(8):
        world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
        change = next((e for e in world["mail"]["inbox"].values()
                       if "calendar-change" in (e.get("labels") or [])), None)
        if change is not None:
            await ctx.goto(f"/mail/message/{change['id']}",
                           reasoning="Manager changed the plan — read it.")
            break
        await ctx.wait(reasoning="Watch for a schedule change before finalizing.")
    # 3) Move the 1:1 with Priya up to 2 PM (14:00).
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    events = world["calendar"]["events"]
    oneonone = next(e for e in events.values()
                    if "priya" in (e.get("title") or "").lower())
    await ctx.goto(f"/calendar/edit/{oneonone['id']}",
                   reasoning="Move the 1:1 from 3 PM up to 2 PM.")
    await ctx.fill("input[data-test-id='input-edit-start']", "14:00")
    await ctx.fill("input[data-test-id='input-edit-end']", "15:00")
    await ctx.click("button[data-test-id='btn-update-event']")
    # 4) DELETE the cancelled Team Sync so 2 PM isn't double-booked.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    events = world["calendar"]["events"]
    sync = next(e for e in events.values()
                if "team sync" in (e.get("title") or "").lower())
    await ctx.goto(f"/calendar/edit/{sync['id']}",
                   reasoning="The 2 PM sync is cancelled — delete it.")
    await ctx.click("button[data-test-id='btn-delete-event']")
    # 5) Reply to Priya with the NEW time.
    await ctx.goto("/mail/compose", reasoning="Tell Priya the new time.")
    await ctx.fill("input[data-test-id='input-compose-to']", "priya@example.com")
    await ctx.fill("input[data-test-id='input-compose-subject']",
                   "Re: Our 1:1 today")
    await ctx.fill("textarea[data-test-id='input-compose-body']",
                   "Hi Priya — our 1:1 has been moved up to 2:00 PM today. "
                   "See you then!")
    await ctx.click("button[data-test-id='btn-send']")


async def solve_m23_offsite_keeps_moving(ctx: BrowserCtx) -> None:
    """Gold trajectory for the tight killer. Derive constraints from the RSVPs,
    order veg-inclusive lunch under budget, WAIT for the attendee swap, book the
    only valid after-3 PM free slot (16:00), then confirm the 4 PM time to each
    attendee — composing FRESH to Dana (not replying to the manager)."""
    import re
    # 1) Burger Barn order: Veggie Burger (Priya is vegetarian) + a Cheeseburger,
    #    well under the $40 cap.
    await ctx.goto("/food/restaurant/r_burger", reasoning="Order the team lunch.")
    await ctx.click("button[data-test-id='btn-add-d_veggie']")
    await ctx.click("button[data-test-id='btn-add-d_classic']")
    await ctx.goto("/food/cart")
    await ctx.click("button[data-test-id='btn-place-food-order']")
    # 2) Watch for the async attendee swap (Sam -> Dana, after 3 PM only).
    dana = "dana@example.com"
    for _ in range(8):
        world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
        swap = next((e for e in world["mail"]["inbox"].values()
                     if "offsite-change" in (e.get("labels") or [])), None)
        if swap is not None:
            mm = re.search(r"[\w.]+@example\.com", swap.get("body", "") or "")
            dana = mm.group(0) if mm else dana
            await ctx.goto(f"/mail/message/{swap['id']}",
                           reasoning="Plan changed — read the new constraints.")
            break
        await ctx.wait(reasoning="Watch for plan changes before finalizing.")
    # 3) Book the lunch at 4 PM — the only free slot after 3 PM (3-4 PM is busy).
    await ctx.goto("/calendar/new", reasoning="Book the lunch after 3 PM.")
    await ctx.fill("input[data-test-id='input-event-title']", "Team Offsite Lunch")
    await ctx.fill("input[data-test-id='input-event-start']", "16:00")
    await ctx.fill("input[data-test-id='input-event-end']", "17:00")
    await ctx.click("button[data-test-id='btn-save-event']")
    # 4) Confirm the 4 PM time to each attendee — Dana via a FRESH compose.
    for who in (dana, "priya@example.com", "alex@example.com"):
        await ctx.goto("/mail/compose", reasoning=f"Confirm the time to {who}.")
        await ctx.fill("input[data-test-id='input-compose-to']", who)
        await ctx.fill("input[data-test-id='input-compose-subject']",
                       "Team lunch — confirmed time")
        await ctx.fill("textarea[data-test-id='input-compose-body']",
                       "Confirmed: our team lunch is at 4:00 PM today at "
                       "Burger Barn. See you there!")
        await ctx.click("button[data-test-id='btn-send']")


async def solve_m19_coupon_minefield(ctx: BrowserCtx) -> None:
    """Read the coupon emails, buy keyboard+mouse on ValueMart (the cheaper
    store), try the salient 50% code (rejected — expired), fall back to the
    valid VALUE10, and place the order under the $125 budget ($121.48)."""
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    deals = [e for e in world["mail"]["inbox"].values()
             if "deals@valuemart.com" in (e.get("sender") or "").lower()]
    for e in deals:
        await ctx.goto(f"/mail/message/{e['id']}",
                       reasoning="Read this ValueMart coupon email.")
    # ValueMart is cheaper; add the keyboard + mouse.
    await ctx.goto("/market/product/vm_kb_mech",
                   reasoning="ValueMart keyboard (cheaper store).")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/product/vm_mouse_wireless")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/cart")
    # The flashy 50% code is expired -> rejected; fall back to the valid 10%.
    await ctx.fill("input[data-test-id='market-input-coupon']", "VALUEMART50")
    await ctx.click("button[data-test-id='market-btn-apply-coupon']")
    await ctx.fill("input[data-test-id='market-input-coupon']", "VALUE10")
    await ctx.click("button[data-test-id='market-btn-apply-coupon']")
    await ctx.click("button[data-test-id='market-btn-place-order']")


async def solve_m18_async_coupon_flip(ctx: BrowserCtx) -> None:
    """Gold 'noticed-the-flip-and-switched' trajectory. Commit to ShopGym
    (initially cheaper with TECH20) -> reaching its checkout fires the async
    flash-sale email -> read VALUEMART30 -> re-evaluate (ValueMart now cheapest)
    -> abandon ShopGym, buy the laptop+keyboard on ValueMart with VALUEMART30."""
    import re
    # 1) Start the ShopGym purchase (laptop + keyboard) and reach checkout —
    #    this fires ShopCheckoutReached, arming the async flip.
    await ctx.goto("/product/p_laptop_studio",
                   reasoning="ShopGym + TECH20 looks cheaper, so start here.")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.goto("/product/p_kb_mech")
    await ctx.click("button[data-test-id='btn-add-to-cart']")
    await ctx.click("a[data-test-id='link-cart']")
    await ctx.click("a[data-test-id='btn-proceed-checkout']")   # -> /checkout/address
    # 2) Wait for the flash-sale email, then read the new coupon code.
    code = "VALUEMART30"
    for _ in range(6):
        world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
        flip = next((e for e in world["mail"]["inbox"].values()
                     if "coupon-flip" in (e.get("labels") or [])), None)
        if flip is not None:
            m = re.search(r"VALUEMART\d+", flip.get("body", "") or "")
            code = m.group(0) if m else code
            await ctx.goto(f"/mail/message/{flip['id']}",
                           reasoning="A bigger ValueMart coupon arrived — read it.")
            break
        await ctx.wait(reasoning="Watch the inbox for a better deal before paying.")
    # 3) Re-evaluate -> ValueMart is now cheapest. Abandon ShopGym, buy there.
    await ctx.goto("/market/product/vm_laptop_studio",
                   reasoning="ValueMart is cheapest with the flip coupon — switch.")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/product/vm_kb_mech")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/cart")
    await ctx.fill("input[data-test-id='market-input-coupon']", code)
    await ctx.click("button[data-test-id='market-btn-apply-coupon']")
    await ctx.click("button[data-test-id='market-btn-place-order']")


async def solve_m17_cross_retailer_cheaper(ctx: BrowserCtx) -> None:
    """Read the ValueMart coupon from email, then buy the monitor on the
    genuinely-cheaper store. ShopGym deal = $199.99 + $5.99 = $205.98;
    ValueMart with VALUE10 = $209.99 x 0.9 = $188.99 (free delivery) -> the
    coupon makes ValueMart cheaper, so order it there with the coupon applied."""
    import re
    # 1) Read the coupon code from the ValueMart email.
    world = ctx.http.get(f"{ctx.server_url}/_harness/world").json()
    coupon_email = next(
        e for e in world["mail"]["inbox"].values()
        if "valuemart" in (e.get("sender") or "").lower()
        and "coupon" in (e.get("subject") or "").lower())
    mm = re.search(r"VALUE\d+", coupon_email.get("body", "") or "")
    code = mm.group(0) if mm else "VALUE10"
    await ctx.goto(f"/mail/message/{coupon_email['id']}",
                   reasoning="Read the ValueMart coupon code.")
    # 2) ValueMart is cheaper AFTER the coupon ($188.99 < $205.98) -> buy there.
    await ctx.goto("/market/product/vm_monitor_24",
                   reasoning="ValueMart is the cheaper store once the coupon applies.")
    await ctx.click("button[data-test-id='market-btn-add-to-cart']")
    await ctx.goto("/market/cart")
    await ctx.fill("input[data-test-id='market-input-coupon']", code)
    await ctx.click("button[data-test-id='market-btn-apply-coupon']")
    await ctx.click("button[data-test-id='market-btn-place-order']")


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
    "M10/dinner_source_conflict":    solve_m10_dinner_source_conflict,
    "M11/cancel_unshipped_over_100": solve_m11_cancel_unshipped_over_100,
    "M12/bulk_add_dense_grid":       solve_m12_bulk_add_dense,
    "M13/order_cleanup_audit":       solve_m13_order_cleanup_audit,
    "M14/return_then_refund":        solve_m14_return_then_refund,
    "M15/inbox_price_watch":         solve_m15_inbox_price_watch,
    "M16/coordinated_dinner_delay":  solve_m16_coordinated_dinner_delay,
    "M17/cross_retailer_cheaper":    solve_m17_cross_retailer_cheaper,
    "M18/async_coupon_flip":         solve_m18_async_coupon_flip,
    "M19/coupon_minefield":          solve_m19_coupon_minefield,
    "M20/errand_run":                solve_m20_errand_run,
    "M21/async_errand_run":          solve_m21_async_errand_run,
    "M22/async_calendar_cascade":    solve_m22_async_calendar_cascade,
    "M23/offsite_keeps_moving":      solve_m23_offsite_keeps_moving,
}
