# M271 / M252 Post-Hardening Cascade Forensic — 2026-07-16

Terminal status: **COMPLETE** (exit 0). Spend ~$7.97. Cap $120 not hit.

## Matrix

| Task | Qwen | GPT-5.1 | GPT-5.5 | Sonnet | stopped_at |
|---|---:|---:|---:|---:|---|
| M271 | 1/3 | — | — | — | qwen |
| M252 | 2/3 | 3/3 | 3/3 | blocked* | sonnet |

\*Sonnet: all 3 seeds zero-step inconclusive — Anthropic credit too low. Not resistance.

## Membership

- **M271** — this tree’s Qwen 1/3 caused a temporary HOLD; later **restored**
  via `trajectories/prepublication_m271_promotion_20260716/cascade/`
  (Qwen 2/3 / GPT-5.1 2/3 / GPT-5.5 3/3) under the **same seeds 0/1/2** —
  seed-0 inference-time variance, not a seed swap (see promotion audit
  disclosure). See
  `docs/history/audits/M271_PROMOTION_RECASCADE_2026-07-16.md`.
- **M252 RETAIN** — clean through GPT-5.5; Sonnet still credit-BLOCKED after
  retries (`../M252_SONNET_CREDIT_BLOCKED.md`).

Full writeup: `docs/history/audits/M271_M252_POST_HARDENING_RESCREEN_2026-07-16.md`.
