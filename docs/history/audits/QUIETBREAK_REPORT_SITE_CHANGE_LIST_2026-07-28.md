# QuietBreak report-site change list — 2026-07-28

Planning + Section 4 lock. **§1 funnel numbers are locked: ~250 → Qwen 85 / GPT-5.1 78 / GPT-5.5 70 / Sonnet 65** (customer-facing; 85 = sellable/Qwen-break story). Retracts prior “drop Qwen” ship and incoherent 112/82/65 mix. Sources: `docs/report-site/Report.dc.html`, `TaskExplorer.dc.html`, `data/tasks6.json`, `trajectories/sellable_breakers_v2.csv`, `TABLE1_STRONGEST_TIER_RECOMPUTE_20260721.json`, `docs/history/plans/CURRENT_WORK_2026-07-21.md`, `PROJECT_INFO.md`, `docs/history/forensics/sol_opus/*`, and the 2026-07-28 best-effort 312-task break census.

**Status updated 2026-07-28 (implementation pass):** checklist items 1–7 done on the public HTML; optional CoT collapse / JSONL scrub still open.

---

## Current page order (shipped)

| # | `id` | What it is |
|---|---|---|
| 01 | `#top` | Hero + 312 / 85 stats |
| 02 | `#why` | Why QuietBreak |
| 03 | `#environment` + apps | Multi-app world |
| 03b | `#taxonomy` | Mechanism families on 83 + 2 specialized |
| **04** | `#comparison` | **Sol vs Opus N=75** (moved above cascade) |
| **05** | `#leaderboard` | **LOCKED: ~250 → 85 / 78 / 70 / 65 with Qwen** |
| 06 | `#methodology` | Reset → classify + gates |
| — | (cta) | Task explorer promo (**four** samples) |
| 07 | `#scope` | Scope / interpretation |

Task Explorer: **four** episodes in `data/tasks6.json` — M95, M213, M76, M312. M47 and M142 cut from explorer UI/data (upload assets may still sit unused).

---

## 1. Section 4 funnel — **LOCKED** (2026-07-28 stakeholder decision; Qwen restored) — **DONE**

### Locked graphic (ship these)

**Customer strip:** out of **~250** adversarially screened tasks → **Qwen 85 · GPT-5.1 78 · GPT-5.5 70 · Sonnet 65**.

| Bar | Number | Customer meaning |
|---|---:|---|
| Denom | **~250** | Adversarially screened tasks (graphic round of exact **N=269**) |
| Qwen | **85** | Broke Qwen (= sellable / release ledger count — accepted clean story) |
| GPT-5.1 | **78** | Broke GPT-5.1 |
| GPT-5.5 | **70** | Broke GPT-5.5 |
| Sonnet | **65** | Broke Sonnet 4.6 — **never use census 83** |

**What `Report.dc.html` ships:** bars **85 / 78 / 70 / 65** (Qwen first) + one-liner caption *“Out of ~250 adversarially screened tasks.”* Keep copy short — **no** long TABLE1 / nested-universe / “No Qwen” footnote.

### Author note (not for the page)

85 is the sellable/Qwen-break story: best clean customer framing from messy evidence. Mid-bars 78 / 70 / 65 remain the TABLE1 independent counts among the 85. Do not paste methodology essays onto the graphic.

### RETRACTED — prior locks

- **Drop-Qwen ship** (bars 78 / 70 / 65 only, “of 85 sellable”) — superseded; Qwen bar restored at **85**.
- **112 / 82 / 65** mix (312 best-effort GPT paired with sellable Sonnet) — incoherent; must not ship.
- Strongest-or-deeper **85 / 84 / 72 / 65** as the §4 claim set — retired as primary framing (numbers may appear as bar heights only under the ~250 story).

**Do not revive 112 / 82 / 65.** Keep 71 / 112 / 82 / 83 only in methods/appendix census tables.

### Nested / source crib (authors)

| Model | N | Source |
|---|---:|---|
| Qwen (graphic) | **85** | Sellable ledger count — customer “broke Qwen” |
| GPT-5.1 | **78** | TABLE1 independent `g51` among 85 |
| GPT-5.5 | **70** | independent `g55` |
| Sonnet | **65** | independent `gson` / Table 1 Sonnet-break |
| Qwen (measured panels) | **31 broke / 34 with evidence** | CSV — sparse; **do not** put “31” on the customer strip |

### ~250 denominator

| Exact N | Label | Source |
|---:|---|---|
| **269** | Adversarially break-screened (strict) | `CURRENT_WORK_2026-07-21.md` / Table 1 denom crib |
| **203** | cascade_v2 latest-wins matrix bookkeeping | same |
| **312** | Live registry (pre-Sheets) | `server.tasks.TASKS` / PROJECT_INFO |
| **~250** | **Graphic round** of **269** | Customer-facing “adversarially screened” denom |

### Best-effort independent breaks on all 312 (appendix only — **not** §4 / §5 cascade)

| Model | Broke ≥2/3 | Have evidence | No evidence |
|---|---:|---:|---:|
| Qwen | **71** | 216 | 96 |
| GPT-5.1 | **112** | 191 | 121 |
| GPT-5.5 | **82** | 129 | 183 |
| Sonnet | **83** | 124 | 188 |

These **do not descend** (5.1 > Qwen) and **Sonnet ≠ 65**. Unfit as the cascade funnel.

### Evidence gaps (authors only; stay off the customer page)

- Qwen panels sparse on sellables (~51/85 missing) — graphic still uses **85** as the accepted sellable/Qwen-break story.
- 65 Sonnet-break ≠ 83 Sonnet≥2/3 across all 312.
- cascade_v2 alone only shows **30** Sonnet≥2/3 in the 203-row stop table; most of the 65 live in **v1-heavy** ledger history.
- Do not revive “~1/3 survive to strongest” for 65/85 (that is 76.5%). The ~1/3 figure is **85/269 ≈ 31.6%** (sellables among adversarially screened).

---

## 2. Task Explorer — keep ~4 / cut 2 — **DONE**

### Kept (4)

| Keep | Why |
|---|---|
| **M95** | Shortest Sonnet demo; customer-safe; content-default |
| **M213** | Distinct mechanism (tool-outcome / false confirmation); multi-app Mail |
| **M76** | Short GPT-5.5 demo; ask-don’t-guess; high clarity |
| **M312** | Implicit-constraint × deference; shows ordinary shopping still fails |

Model mix: **3 Sonnet + 1 GPT-5.5**.

### Cut (2)

| Cut | Why |
|---|---|
| **M47** | Native dropdown motor struggle — highest customer-risk sample |
| **M142** | Infeasibility + rating floor looks like a catalog/UI setup trick |

### Editorial / data follow-ups — **DONE**

- [x] Shrink explorer data to 4 tasks in `data/tasks6.json` (filename kept; content is 4 rows)
- [x] Report CTA + Task Explorer hero: “six” → “four”; tab grid `repeat(4)`
- [x] M76 copy: “cancels under ambiguity” (not “cancels one”)
- [x] M312 fairness: no “Bucket B” jargon
- [ ] Optional: remove unused M47/M142 webm + jsonl from `uploads/` (left in tree for now)

---

## 3. Revealing / bad-info cut list (external customers)

### Cut or rewrite (high priority) — **DONE** on public HTML

| Location | Issue | Action | Status |
|---|---|---|---|
| Report `#environment` / Shared state | Names internal `WorldState` | Say “one shared application state” | **DONE** |
| Report apps blurb | `update_event` overlap guard | **Cut** | **DONE** |
| Report methodology | harness / Set-of-Mark | Softened to evaluation driver / annotated screenshots | **DONE** |
| Task Explorer provenance | harness vs agent report | Softened: ground-truth application state | **DONE** |
| Task Explorer M312 fairness | Bucket B | Rewritten without fairness buckets | **DONE** |
| Task Explorer M95 seed/failure | “hidden from review” framing | Softened; stress cart-path visibility | **DONE** |
| Task Explorer M47 | Native-select thrash | **Cut episode** | **DONE** |
| Report Sol/Opus footer | fairness rejects / significance | Softened; rejects omitted from strip | **DONE** |
| Report taxonomy footnotes | Injection + source-anchoring gray “footnote” bars | Separate under-graph resistance cards; no “footnote”/ledger jargon | **DONE** |
| JSONL downloads | localhost / internal paths | Prefer scrubbed exports | **OPEN** (optional) |
| Scope cards | Fine overall | Keep | **DONE** (unchanged) |

### Soften (medium)

| Item | Note | Status |
|---|---|---|
| Full agent chain-of-thought in the step panel | Default collapsed “show reasoning” | **OPEN** (optional) |
| Token counts / episode IDs / seed badges | Optional hide | **OPEN** (optional) |
| “~750 verifier tests” | Fine if true | Kept |
| Oracle gate copy | Softened to “safe completion path verified before screening” | **DONE** |

### Do **not** surface on the public site

- Verifier bug forensics, M271 volatility / seed-0 hinge, M56 hold, M297/M298 rejects (except maybe a single anonymized “two comparison tasks excluded”)
- Credit-BLOCKED / incomplete mid-cascade counts
- Motor-vs-reasoning Section 1C internals
- Sellable CSV paths, shard logs, GCP/Gemini census

---

## 4. Sol / Opus — move up + rewrite notes — **DONE**

### What the N=75 story is (from PROJECT_INFO + SOL_OPUS docs)

- **Track:** closed **comparison**, not the sellable promotion path.
- **Set:** flagship20 ∪ xmodel37 ∪ xmodel18 = **75** (thin-vein M342–M350 **discarded**).
- **Raw ≥2/3:** Sol **40/75**, Opus **30/75**, overlap **25**, Sol-only **15**, Opus-only **5**, union **45**.
- **Forensic:** **43** confirmed genuine; **2** rejected (M297 Bucket C; M298 seed-satisfied gate) — **authors only**; not on v1.0 hero strip.
- **Venn vs sellables:** 75 is **neither subset nor superset** of the 85 (`|A ∩ B| = 63`).

### Placement — **DONE**

`#comparison` is **04**, immediately before `#leaderboard` (**05**). Nav: Sol / Opus → Cascade.

### Copy — **DONE**

- Lead: same fixed 75, same protocol → directly comparable; Sol **40** vs Opus **30**; **25** shared.
- Removed: historical cohort / protocol-differs / breaker-enriched / fairness rejects / significance disclaimer dump.

**Do not claim:** Sol/Opus raw breaks ⊆ sellable 85; population-wide ranking; statistical significance.

---

## 5. Ordered implementation checklist

1. **Lock funnel numbers** — **DONE:** ship **~250 → Qwen 85 / GPT-5.1 78 / GPT-5.5 70 / Sonnet 65**.
2. **Rewrite cascade bars + caption** — **DONE.**
3. **Move Sol/Opus block above cascade**; renumber section labels / sticky nav — **DONE.**
4. **Rewrite Sol/Opus copy** per §4 — **DONE.**
5. **Cut Task Explorer to 4:** M95, M213, M76, M312; cut M47, M142 — **DONE.**
6. **Update** Report CTA, explorer hero stats, tab grid, `data/tasks*.json` — **DONE.** Orphaned uploads cleanup optional.
7. **Sanitize revealing copy:** WorldState, overlap-guard, Bucket B, harness/mark_id, M95 framing, taxonomy footnotes, Sol/Opus disclaimer — **DONE.**
8. **Optional:** collapse long CoT by default; scrub JSONL downloads for localhost / internal paths — **STILL OPEN.**
9. **QA pass:** numbers match TABLE1 + CURRENT_WORK denom crib; Sol/Opus still 40/30/25/15/5; no sellable CSV edits — **DONE** (spot-check on this pass).
10. **Ship** report-site HTML after checklist 1–7 — this audit doc tracks status; optional item 8 can follow.

---

## Appendix — quick source map

| Claim | Where |
|---|---|
| 65 / 7 / 12 / 1 strongest tiers | `sellable_breakers_v2.csv` + TABLE1 audit |
| 78 / 70 / 65 independent among 85 | TABLE1 JSON `g51` / `g55` / `gson` |
| 269 adversarially screened; 203 v2 | `CURRENT_WORK_2026-07-21.md` §B |
| 312 registry; 85 ledger | `PROJECT_INFO.md` |
| Sol/Opus 40/30/25/15/5 on 75 | `PROJECT_INFO.md` §2A; `SOL_OPUS_SELLABLE_VENN.md` |
| Qwen sparse on sellables | CSV `models_broken` (34 present / 31 ≥2/3); graphic still uses **85** |
| 312 best-effort 71/112/82/83 | 2026-07-28 census; **archived — not cascade graphic**. Cascade locks **85/78/70/65 with Qwen** |
| Shipped §4 / §5 order | `Report.dc.html` `#comparison` then `#leaderboard` |

*End of change list.*
