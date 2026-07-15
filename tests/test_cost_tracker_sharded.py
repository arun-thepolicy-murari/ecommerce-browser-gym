# -*- coding: utf-8 -*-
"""Regression tests for eval.cost_tracker.cost_of_tree — the layout-independent
budget accountant.

These lock the fix for a real Phase-1 safeguard bug: the budget cap billed by
DIRECTORY (root/<tier>/*.jsonl), which is correct for a flat single-process run
but returned $0 for SHARDED parallel runs (root/shard_N/<tier>/*.jsonl). During
the parallel batches the cap was therefore NOT enforced — each shard policed only
its own ~1/N slice, so the effective ceiling was up to N x the intended cap.

cost_of_tree() fixes this by recursing the whole tree and billing each episode at
the rate of the model in its ``agent_name`` (not its directory). The tests below
build a synthetic sharded tree and assert:
  1. cost_of_tree bills a sharded layout correctly (the exact bug that shipped);
  2. the OLD dir-keyed cost_report returns $0 on that same layout (documents the
     failure mode so nobody "optimizes" the recursion away);
  3. billing follows agent_name, not the directory a file happens to sit in.
"""
from __future__ import annotations

import json
import os

from eval.cost_tracker import (
    cost_of_tree,
    cost_report,
    rates_per_token,
    _DEFAULT_RATES_PER_M,
)


def _episode(agent_name, steps):
    """Minimal trajectory record matching the real .jsonl schema fields the
    accountant reads (agent_name + steps[].tokens_in/tokens_out)."""
    return {
        "agent_name": agent_name,
        "steps": [{"tokens_in": ti, "tokens_out": to} for ti, to in steps],
    }


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def _build_sharded_tree(root):
    """A 3-shard tree, tiers nested under shard_N/ exactly like cascade_parallel
    writes them. Known token counts per tier so the expected cost is exact."""
    # 1,000,000 in / 100,000 out per tier — round numbers keep the math obvious.
    layout = {
        "shard_0/qwen":    "qwen[qwen/qwen3-vl-235b-a22b-instruct]",
        "shard_1/gpt-5.1": "openai_pixel[gpt-5.1]",
        "shard_1/gpt-5.5": "openai_pixel[gpt-5.5]",
        "shard_2/sonnet":  "pixel[claude-sonnet-4-6]",
    }
    for rel, agent in layout.items():
        _write(os.path.join(root, rel, "ep__0__x.jsonl"),
               _episode(agent, [(600_000, 60_000), (400_000, 40_000)]))  # =1M in / 100k out
    return layout


def _expected_total():
    r = _DEFAULT_RATES_PER_M
    # one tier-episode each, 1M in + 0.1M out, at $/M rates
    total = 0.0
    for tier in ("qwen", "gpt-5.1", "gpt-5.5", "sonnet"):
        total += 1.0 * r[tier]["in"] + 0.1 * r[tier]["out"]
    return total


def test_cost_of_tree_bills_sharded_layout(tmp_path):
    root = str(tmp_path / "batch")
    _build_sharded_tree(root)
    total, rows = cost_of_tree(root, verbose=False)
    assert abs(total - _expected_total()) < 1e-9, (total, _expected_total())
    # every tier registered exactly one episode
    by_tier = {t: n for (t, n, *_rest) in rows if n}
    assert by_tier == {"qwen": 1, "gpt-5.1": 1, "gpt-5.5": 1, "sonnet": 1}


def test_old_dir_keyed_report_is_blind_to_shards(tmp_path):
    """Documents the bug: dir-keyed cost_report finds no root/<tier>/ dirs in a
    sharded tree and reports $0 — the exact miscount that let the cap go unenforced."""
    root = str(tmp_path / "batch")
    _build_sharded_tree(root)
    total, _ = cost_report(root, cap=None)
    assert total == 0.0


def test_billing_follows_agent_name_not_directory(tmp_path):
    """A sonnet episode misfiled under a qwen/ directory must still bill at the
    sonnet rate — billing keys on the model, not the folder."""
    root = str(tmp_path / "batch")
    _write(os.path.join(root, "shard_0/qwen/misfiled.jsonl"),
           _episode("pixel[claude-sonnet-4-6]", [(1_000_000, 100_000)]))
    total, rows = cost_of_tree(root, verbose=False)
    r = _DEFAULT_RATES_PER_M["sonnet"]
    assert abs(total - (1.0 * r["in"] + 0.1 * r["out"])) < 1e-9
    assert {t: n for (t, n, *_rest) in rows}["sonnet"] == 1
    assert {t: n for (t, n, *_rest) in rows}["qwen"] == 0


def test_paid_openrouter_hy3_rate(tmp_path):
    root = str(tmp_path / "external_comparison")
    _write(os.path.join(root, "hy3/ep__0__x.jsonl"),
           _episode("openai[tencent/hy3]", [(1_000_000, 100_000)]))
    total, rows = cost_of_tree(root, verbose=False)
    rate = _DEFAULT_RATES_PER_M["hy3"]
    assert rate == {"in": 0.14, "out": 0.58}
    assert abs(total - (rate["in"] + 0.1 * rate["out"])) < 1e-9
    assert {t: n for (t, n, *_rest) in rows}["hy3"] == 1


def test_free_openrouter_hy3_has_zero_cost(tmp_path):
    root = str(tmp_path / "free_smoke")
    _write(os.path.join(root, "hy3/ep__0__x.jsonl"),
           _episode("openai[tencent/hy3:free]", [(1_000_000, 100_000)]))
    total, rows = cost_of_tree(root, verbose=False)
    assert total == 0.0
    by_tier = {t: n for (t, n, *_rest) in rows}
    assert by_tier["hy3-free"] == 1
    assert by_tier["hy3"] == 0


def test_cap_would_halt_globally_across_shards(tmp_path):
    """The safeguard's whole point: summed across shards, spend crosses the cap.
    Per-shard, no single slice does — which is why the old per-shard check never
    fired. cost_of_tree over the shared parent is what makes the cap load-bearing."""
    root = str(tmp_path / "batch")
    _build_sharded_tree(root)
    global_total, _ = cost_of_tree(root, verbose=False)
    per_shard = [cost_of_tree(os.path.join(root, s), verbose=False)[0]
                 for s in ("shard_0", "shard_1", "shard_2")]
    cap = global_total - 0.01              # a cap the GLOBAL total exceeds...
    assert global_total >= cap             # ...global check would halt
    assert all(s < cap for s in per_shard)  # ...but no individual shard would
