"""Control-plane authentication and reset-isolation regressions."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from fastapi.testclient import TestClient
import httpx
import pytest

from harness.auth import HARNESS_TOKEN_ENV, HARNESS_TOKEN_HEADER
from harness.runner import open_browser
from server.main import app


TOKEN = "deterministic-test-token"
AUTH = {HARNESS_TOKEN_HEADER: TOKEN}
ROUTES = (
    ("GET", "/_harness/tasks", None),
    ("POST", "/_harness/reset", {"task_id": "A1/buy_wireless_mouse", "seed": 0}),
    ("GET", "/_harness/state", None),
    ("GET", "/_harness/world", None),
    ("GET", "/_harness/snapshot", None),
    ("POST", "/_harness/verify", {"url": "/", "step": 0}),
    ("POST", "/_harness/tick", {"step": 0}),
    ("POST", "/_harness/classify_failure", {"success": True, "score": 1.0}),
)


@pytest.mark.parametrize(("method", "path", "payload"), ROUTES)
def test_harness_routes_reject_missing_and_wrong_tokens(
    monkeypatch, method: str, path: str, payload: dict | None,
) -> None:
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    with TestClient(app) as client:
        assert client.request(method, path, json=payload).status_code == 401
        assert client.request(
            method,
            path,
            json=payload,
            headers={HARNESS_TOKEN_HEADER: "wrong-token"},
        ).status_code == 401


def test_correct_token_can_reset_and_read_control_state(monkeypatch) -> None:
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    with TestClient(app) as client:
        reset = client.post(
            "/_harness/reset",
            headers=AUTH,
            json={"task_id": "A1/buy_wireless_mouse", "seed": 0},
        )
        assert reset.status_code == 200
        assert client.get("/_harness/world", headers=AUTH).status_code == 200


def test_all_harness_routes_accept_correct_token(monkeypatch) -> None:
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    with TestClient(app) as client:
        client.post(
            "/_harness/reset",
            headers=AUTH,
            json={"task_id": "A1/buy_wireless_mouse", "seed": 0},
        ).raise_for_status()
        for method, path, payload in ROUTES:
            response = client.request(method, path, headers=AUTH, json=payload)
            assert response.status_code == 200, (method, path, response.text)


def test_browser_navigation_cannot_read_or_reset_world(monkeypatch) -> None:
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    with TestClient(app) as browser:
        assert browser.get("/_harness/world").status_code == 401
        assert browser.post(
            "/_harness/reset",
            json={"task_id": "A1/buy_wireless_mouse", "seed": 0},
        ).status_code == 401


def test_authenticated_reset_preserves_episode_isolation(monkeypatch) -> None:
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    with TestClient(app) as client:
        payload = {"task_id": "A1/buy_wireless_mouse", "seed": 0}
        client.post("/_harness/reset", headers=AUTH, json=payload).raise_for_status()
        mutation = client.post(
            "/api/cart/add",
            data={"product_id": "p_mouse_wireless", "quantity": 1},
            follow_redirects=False,
        )
        assert mutation.status_code == 303
        dirty = client.get("/_harness/snapshot", headers=AUTH).json()
        assert dirty["cart_item_count"] == 1

        client.post("/_harness/reset", headers=AUTH, json=payload).raise_for_status()
        clean = client.get("/_harness/snapshot", headers=AUTH).json()
        assert clean["cart_item_count"] == 0


def test_real_browser_context_cannot_access_control_plane(monkeypatch) -> None:
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    repo = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, HARNESS_TOKEN_ENV: TOKEN}
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "server.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                if httpx.get(base, timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise AssertionError("test server did not start")

        async def check_browser() -> None:
            pw, browser, context, page = await open_browser(
                server_url=base,
                headless=True,
                record_video=False,
                inject_cursor=False,
            )
            try:
                response = await page.goto(f"{base}/_harness/world")
                assert response is not None and response.status == 401
                assert TOKEN not in await page.content()
                assert await page.evaluate(
                    "(token) => Object.values(localStorage).includes(token)", TOKEN
                ) is False
                reset_status = await page.evaluate(
                    """async () => (await fetch('/_harness/reset', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            task_id: 'A1/buy_wireless_mouse', seed: 0
                        })
                    })).status"""
                )
                assert reset_status == 401
            finally:
                await context.close()
                await browser.close()
                await pw.stop()

        asyncio.run(check_browser())
        trusted = httpx.post(
            f"{base}/_harness/reset",
            headers=AUTH,
            json={"task_id": "A1/buy_wireless_mouse", "seed": 0},
        )
        assert trusted.status_code == 200
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_authenticated_oracle_episode_uses_real_control_plane(
    monkeypatch, tmp_path: Path,
) -> None:
    """Exercise the production reset, BrowserCtx probes, and final verifier."""
    monkeypatch.setenv(HARNESS_TOKEN_ENV, TOKEN)
    repo = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, HARNESS_TOKEN_ENV: TOKEN}
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "server.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                if httpx.get(base, timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise AssertionError("test server did not start")

        from eval.run import _run_one

        trajectory = asyncio.run(_run_one(
            agent_kind="oracle",
            task_id="A1/buy_wireless_mouse",
            seed=0,
            server_url=base,
            headless=True,
            record_video=False,
            out_traj_dir=tmp_path / "trajectories",
            out_screens_dir=tmp_path / "screenshots",
            llm_model=None,
        ))

        assert trajectory.error is None
        assert trajectory.initial_snapshot["cart_item_count"] == 0
        assert trajectory.steps
        assert all(step.snapshot_after for step in trajectory.steps)
        assert trajectory.verifier_result["success"] is True
        assert trajectory.verifier_result["score"] == 1.0
    finally:
        proc.terminate()
        proc.wait(timeout=10)
