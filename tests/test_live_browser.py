"""Live browser service — ticket auth, origin policy, coordinate transform.

These are the pure-logic guarantees behind the stream. The full end-to-end proof
(frames + a click landing on a real page) needs a running gym and browser and
lives in the spike script; what must never silently regress is here.
"""

from __future__ import annotations

import time

import pytest

from live_browser import service


# --------------------------------------------------------------------------- tickets
def test_ticket_roundtrips_for_an_email_owner():
    """Regression: owners are emails, which contain dots. A dot-delimited ticket
    parsed the wrong fields and rejected every legitimate connection."""
    t = service.mint_ticket("sess123", "diego@deccan.ai")
    assert service.check_ticket("sess123", t) == "diego@deccan.ai"


@pytest.mark.parametrize("owner", ["a@b.co", "first.last+tag@sub.domain.example", "plain", "üser@dömain.io"])
def test_ticket_roundtrips_for_awkward_owners(owner):
    t = service.mint_ticket("s", owner)
    assert service.check_ticket("s", t) == owner


def test_ticket_is_scoped_to_its_session():
    """A ticket for one workspace must not open another — otherwise any annotator
    with a valid ticket could attach to someone else's live browser."""
    t = service.mint_ticket("sessA", "u@x.io")
    assert service.check_ticket("sessA", t) == "u@x.io"
    assert service.check_ticket("sessB", t) is None


def test_expired_ticket_is_rejected():
    assert service.check_ticket("s", service.mint_ticket("s", "u@x.io", ttl=-1)) is None


def test_tampered_ticket_is_rejected():
    t = service.mint_ticket("s", "u@x.io")
    exp, sig, owner_b64 = t.split(".", 2)
    # forge a later expiry, keep the old signature
    assert service.check_ticket("s", f"{int(exp) + 99999}.{sig}.{owner_b64}") is None
    # swap the owner, keep the signature
    assert service.check_ticket("s", f"{exp}.{sig}.{service._b64(b'attacker@evil.io')}") is None


@pytest.mark.parametrize("bad", ["", "garbage", "1.2", "notanint.sig.b3Vy", "..."])
def test_malformed_tickets_do_not_raise(bad):
    assert service.check_ticket("s", bad) is None


# --------------------------------------------------------------------------- origin
def test_origin_allowlist(monkeypatch):
    monkeypatch.setattr(service, "ALLOWED_ORIGINS", ["http://localhost:8080"])
    assert service.origin_ok("http://localhost:8080")
    assert not service.origin_ok("http://evil.example")
    assert not service.origin_ok(None)


def test_origin_wildcard_is_permissive(monkeypatch):
    monkeypatch.setattr(service, "ALLOWED_ORIGINS", ["*"])
    assert service.origin_ok("http://anything.example")


# --------------------------------------------------------------------------- coordinates
def _sess() -> service.LiveSession:
    return service.LiveSession(id="s", owner="u@x.io", url="http://localhost:8000/")


def test_normalized_coordinates_map_to_the_viewport():
    """The wire format is a FRACTION of the client canvas, so a scaled canvas can
    never mis-place a click: the service always multiplies by the real viewport."""
    s = _sess()
    assert s.to_page_xy(0.0, 0.0) == (0.0, 0.0)
    assert s.to_page_xy(1.0, 1.0) == (float(service.VIEWPORT_W), float(service.VIEWPORT_H))
    assert s.to_page_xy(0.5, 0.5) == (service.VIEWPORT_W / 2, service.VIEWPORT_H / 2)


def test_the_same_fraction_lands_identically_whatever_the_canvas_size():
    """A 900x563 and a 1920x1200 canvas both send the same fraction for the same
    on-screen point, and both must resolve to the same page pixel."""
    s = _sess()
    target_x, target_y = 1039.0, 72.0  # a real element position in page pixels
    for canvas_w, canvas_h in [(900, 563), (1920, 1200), (640, 400), (1280, 800)]:
        # what the client computes from ITS canvas
        client_px_x = target_x / service.VIEWPORT_W * canvas_w
        client_px_y = target_y / service.VIEWPORT_H * canvas_h
        nx, ny = client_px_x / canvas_w, client_px_y / canvas_h
        x, y = s.to_page_xy(nx, ny)
        assert x == pytest.approx(target_x, abs=0.001)
        assert y == pytest.approx(target_y, abs=0.001)


def test_out_of_range_coordinates_are_clamped_not_thrown():
    """A drag that leaves the canvas must not dispatch input outside the page."""
    s = _sess()
    assert s.to_page_xy(-5.0, -5.0) == (0.0, 0.0)
    assert s.to_page_xy(9.0, 9.0) == (float(service.VIEWPORT_W), float(service.VIEWPORT_H))
