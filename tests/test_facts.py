"""Pure-logic tests for the per-step fact extractors (harness/facts.py).

No browser: extractors are pure functions over a world-snapshot dict.
"""

from __future__ import annotations

from harness.facts import get_fact_extractor, _facts_m2, _facts_m3


def test_m2_extractor_pulls_order_id_and_tracking():
    world = {
        "shop": {"orders": {"ORD-1042": {"total": 24.99}}},
        "mail": {"inbox": {
            "em_9": {"order_id": "ORD-1042",
                     "tracking_url": "/account/orders/ORD-1042/track",
                     "labels": ["orders"]},
            "em_1": {"order_id": None, "tracking_url": None,
                     "labels": ["updates"]},
        }},
    }
    f = _facts_m2(world, "/account/orders/ORD-1042/track")
    assert f["shop.order_id"] == "ORD-1042"
    assert f["mail.order_id"] == "ORD-1042"
    assert f["mail.tracking_url"] == "/account/orders/ORD-1042/track"


def test_m2_extractor_empty_before_order():
    # Mid-episode the world may have no order / no confirmation yet.
    assert _facts_m2({"shop": {"orders": {}}, "mail": {"inbox": {}}}, "/") == {}
    assert _facts_m2({}, "/") == {}                  # defensive: missing keys


def test_m3_extractor_pulls_food_and_receipt():
    world = {
        "food": {"orders": {"FOOD-1041": {"total": 16.00}}},
        "mail": {"inbox": {
            "em_5": {"order_id": "FOOD-1041", "amount_total": 16.00,
                     "eta": "7:20 PM", "labels": ["receipts"]},
        }},
    }
    f = _facts_m3(world, "/mail")
    assert f["food.order_id"] == "FOOD-1041"
    assert f["food.total"] == 16.00
    assert f["mail.receipt_total"] == 16.00
    assert f["mail.eta"] == "7:20 PM"


def test_registry_maps_only_cross_app_tasks():
    assert get_fact_extractor("M2/order_then_track_via_email") is _facts_m2
    assert get_fact_extractor("M3/dinner_then_receipt") is _facts_m3
    assert get_fact_extractor("A1/buy_wireless_mouse") is None
