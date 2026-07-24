"""The gym's ids and timestamps must be derived, never random.

The whole project rests on a byte-reproducible reset: fork-before-step-N, replay
validation and the golden export all compare world hashes. `secrets.token_hex`
and `datetime.now()` broke that by construction — a minted id lands in the order
record, the confirmation email, the tracking URL and the cross-app event payload,
so ONE random id makes every world from that action onward differ.

Measured across the archive before the fix: the step at which a run's first
random id appeared predicted its replay coverage exactly, five for five
(M57 17 steps/first id at step 4 -> 4 worlds reconstructed; M70 14/13 -> 13).
"""

from __future__ import annotations

import json

import pytest

from server import mutations
from server.apps import statecodec
from server.main import SESSION, _reset_inline

TASK = "A1/buy_wireless_mouse"


def _buy(state):
    mutations.add_to_cart(state, "p_mouse_wireless", 1)
    return mutations.place_order(state, "pay_visa", "addr_home")


def _fresh(task: str = TASK, seed: int = 0):
    _reset_inline(task, seed)
    return SESSION.current


def _fingerprint(state) -> dict:
    return {
        "lines": [i.id for i in state.cart.items],
        "orders": sorted(state.orders),
        "tracking": sorted(s.tracking_number for o in state.orders.values() for s in (o.shipments or [])),
        "placed": sorted(o.placed_at for o in state.orders.values()),
    }


# --------------------------------------------------------------------------- the bug
def test_the_same_actions_from_the_same_seed_produce_the_same_world():
    """THE regression. Every id and timestamp a checkout mints was random, so two
    replays of one action diverged and every downstream hash comparison failed."""
    first = _fingerprint((lambda s: (_buy(s), s)[1])(_fresh()))
    second = _fingerprint((lambda s: (_buy(s), s)[1])(_fresh()))
    assert first == second, "the same actions from the same seed must reach the same world"
    assert first["orders"], "the probe has to actually place an order, or it proves nothing"


def test_timestamps_are_derived_from_the_clock_not_the_wall():
    """Two runs differed by microseconds, which is all a hash comparison needs."""
    a = _fingerprint((lambda s: (_buy(s), s)[1])(_fresh()))["placed"]
    b = _fingerprint((lambda s: (_buy(s), s)[1])(_fresh()))["placed"]
    assert a == b
    assert a[0].startswith("2026-01-01"), "derived from the epoch, not today"


# --------------------------------------------------------------------------- still usable ids
def test_two_entities_created_in_one_step_do_not_collide():
    """Determinism must not be bought with duplicate primary keys."""
    state = _fresh()
    _buy(state)
    _buy(state)
    ids = sorted(state.orders)
    assert len(ids) == len(set(ids)) == 2, f"colliding order ids: {ids}"


def test_a_different_seed_gives_different_ids():
    """Otherwise two tasks' samples would reference the same order id and a
    dataset consumer could not tell them apart."""
    a = sorted((lambda s: (_buy(s), s)[1])(_fresh(seed=0)).orders)
    b = sorted((lambda s: (_buy(s), s)[1])(_fresh(seed=1)).orders)
    assert a != b


def test_a_minted_id_never_collides_with_a_seeded_fixture_id():
    """Fixtures use readable ids (`pay_visa`) or hyphens (`ORD-5290`); a minted
    one overwriting a seeded record would corrupt the task's own setup."""
    state = _fresh()
    user = state.users[state.current_user_id]
    seeded = set(state.orders) | set(user.addresses) | set(user.payment_methods)
    _buy(state)
    assert not (set(state.orders) - seeded) & seeded


def test_timestamps_still_sort_in_the_order_things_happened():
    """verifiers.py sorts orders by `placed_at`; a constant would break that."""
    state = _fresh()
    _buy(state)
    state.step += 1
    _buy(state)
    stamps = [o.placed_at for o in state.orders.values()]
    assert stamps == sorted(stamps) and len(set(stamps)) == 2


# --------------------------------------------------------------------------- restore
def test_continuing_from_a_restored_checkpoint_does_not_remint_an_existing_id():
    """The counter is deliberately NOT serialized — `apply_snapshot` overlays only
    the mutable slice, so anything stored would come back as zero. It survives
    because the STEP CLOCK is restored and a fork always resumes at a step
    boundary. If that reasoning were wrong, the first order placed after a restore
    would silently overwrite the one already in the world."""
    state = _fresh()
    state.step = 3
    _buy(state)
    before = sorted(state.orders)
    snapshot = json.loads(json.dumps(SESSION.world.to_json()))

    _reset_inline(TASK, 0)
    statecodec.apply_snapshot(SESSION.world, snapshot)
    restored = SESSION.current
    restored.step = 4
    assert sorted(restored.orders) == before
    assert not restored.mint_counts, "the counter starts empty after a restore"

    _buy(restored)
    after = sorted(restored.orders)
    assert len(after) == len(set(after)) == 2, f"restore reminted an existing id: {after}"


def test_the_same_continuation_from_one_checkpoint_replays_identically():
    """What fork-before-step-N depends on: the correction has to land in the same
    world every time it is replayed."""
    state = _fresh()
    state.step = 3
    _buy(state)
    snapshot = json.loads(json.dumps(SESSION.world.to_json()))

    def continue_once():
        _reset_inline(TASK, 0)
        statecodec.apply_snapshot(SESSION.world, snapshot)
        SESSION.current.step = 4
        _buy(SESSION.current)
        return _fingerprint(SESSION.current)

    assert continue_once() == continue_once()


def test_the_bookkeeping_never_reaches_the_serialized_world():
    """It is not task state. In the snapshot it would change the world shape and
    invalidate every hash recorded before this change."""
    assert "mint_counts" not in _fresh().to_json()
