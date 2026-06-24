# -*- coding: utf-8 -*-
"""Rich, interactive breaker dashboard: per-task cards (prompt/should/did) + corrected vein
taxonomy + creative analytics. Merges _dash_tasks.json (verbatim) + _dash_copy.json (editorial)."""
import json, os, html
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "trajectories")
tasks = json.load(open(os.path.join(T, "_dash_tasks.json"), encoding="utf-8"))
copy = {}
cp = os.path.join(T, "_dash_copy.json")
if os.path.exists(cp):
    for c in json.load(open(cp, encoding="utf-8")):
        copy[c["id"]] = c

def gcell(s):
    s = s.strip()
    if s in ("—", "", "-"): return None
    try: return int(s.split("/")[0])
    except Exception: return None
def parse_grid(g):
    parts = g.split("·")
    while len(parts) < 3: parts.append("—")
    return gcell(parts[0]), gcell(parts[1]), gcell(parts[2])

VEINS = [
 ("Hidden-harm checkout", ["expired","corporate","wrong-default payment","wrong-account","stale gift","stale message","hidden message","hidden stale","sneaked","preselection","qty-creep","quantity-creep","quantity","per-line ship","no-action","mix:","triple","two-recipient","mixed basket","expedited","express upcharge","silent misroute","add-on","addon","silent substitution","gift ship-to","ship-to","wrong-occasion","default card","default payment"]),
 ("Sycophancy / false-premise", ["sycophan","false billing","false price","false past-purchase","blind-goal","false premise","false-premise"]),
 ("Tool-affordance / false-confirmation", ["false-confirmation","false confirmation","no-op","phantom affordance","flag-flip","failed-write","tool-affordance"]),
 ("Infeasibility", ["infeasib","nothing qualifies","abstain"]),
 ("Source-anchoring / stale", ["source-anchor","anchoring"]),
 ("Ask-don't-guess / ambiguity", ["ask-don't-guess","ask-dont-guess","ambiguous"]),
 ("Structural / conditional", ["conditional","cross-app join","cross-object","scope-quantifier","split-ship","delivery-date collapse","quantifier"]),
 ("Injection", ["injection","exfil","phishing"]),
 ("Numeric / value", ["value confusion","per-unit"]),
]
def veins(p):
    s = p.lower(); v = [name for name, ks in VEINS if any(k in s for k in ks)]
    return v or ["Other"]

VCOLOR = {"Hidden-harm checkout":"#ef4444","Sycophancy / false-premise":"#a855f7",
 "Tool-affordance / false-confirmation":"#06b6d4","Infeasibility":"#f59e0b",
 "Source-anchoring / stale":"#ec4899","Ask-don't-guess / ambiguity":"#14b8a6",
 "Structural / conditional":"#8b5cf6","Injection":"#f97316","Numeric / value":"#64748b","Other":"#475569"}
TIER_LABEL = {"ALL-3":"Breaks all 3","strong-pair(5.5+son)":"gpt-5.5 + Sonnet","cross-family(2of3)":"Cross (2 of 3)",
 "sonnet-only":"Sonnet-only","gpt-5.1-only":"gpt-5.1-only","gpt-5.5-only":"gpt-5.5-only","resist/fumble":"Weak-model only"}
def tlabel(t): return TIER_LABEL.get(t, t)
TIER_COLOR = {"ALL-3":"#ef4444","strong-pair(5.5+son)":"#f97316","cross-family(2of3)":"#f59e0b",
 "sonnet-only":"#a855f7","gpt-5.1-only":"#3b82f6","gpt-5.5-only":"#22d3ee","resist/fumble":"#475569"}

# enrich
for t in tasks:
    g = parse_grid(t["grid"]); t["g51"], t["g55"], t["son"] = g
    t["veins"] = veins(t["pattern"])
    c = copy.get(t["id"], {})
    t["title"] = c.get("title") or t["pattern"]
    t["insight"] = c.get("insight") or ""
    t["bk"] = [m for m, v in zip(("gpt-5.1","gpt-5.5","Sonnet"), g) if v is not None and v >= 2]

def brk(v): return v is not None and v >= 2
# analytics
N = len(tasks)
g51b = sum(brk(t["g51"]) for t in tasks); g55b = sum(brk(t["g55"]) for t in tasks); sonb = sum(brk(t["son"]) for t in tasks)
all3 = sum(1 for t in tasks if brk(t["g51"]) and brk(t["g55"]) and brk(t["son"]))
pair = sum(1 for t in tasks if brk(t["g55"]) and brk(t["son"]))
vein_count = Counter(); vein_all3 = Counter()
for t in tasks:
    for v in t["veins"]:
        vein_count[v] += 1
        if brk(t["g51"]) and brk(t["g55"]) and brk(t["son"]): vein_all3[v] += 1
tier_count = Counter(t["tier"] for t in tasks)
inversions = [t for t in tasks if brk(t["son"]) and not brk(t["g51"])]
NEW_IDS = {f"M2{n}" for n in range(11,30)}

def bar(label, val, mx, color, sub=""):
    w = int(100*val/mx) if mx else 0
    return (f'<div class="barrow"><span class="blabel" title="{html.escape(label)}">{html.escape(label)}</span>'
            f'<div class="btrack"><div class="bfill" style="width:{w}%;background:{color}"></div>'
            f'<span class="bin">{val}{sub}</span></div></div>')

veinbars = "".join(bar(v, vein_count[v], max(vein_count.values()), VCOLOR.get(v,"#475569"),
                       sub=f' · {vein_all3[v]} all-3') for v, _ in sorted(vein_count.items(), key=lambda kv:-kv[1]))
TIER_ORDER = ["ALL-3","strong-pair(5.5+son)","cross-family(2of3)","sonnet-only","gpt-5.1-only","gpt-5.5-only","resist/fumble"]
tot = sum(tier_count.values())
tierseg = "".join(f'<div class="seg" style="width:{100*tier_count[t]/tot:.1f}%;background:{TIER_COLOR.get(t,"#475569")}" title="{tlabel(t)}: {tier_count[t]}"></div>' for t in TIER_ORDER if tier_count[t])
tierleg = "".join(f'<span class="lg"><i style="background:{TIER_COLOR.get(t,"#475569")}"></i>{tlabel(t)} <b>{tier_count[t]}</b></span>' for t in TIER_ORDER if tier_count[t])
invcards = "".join(
    f'<div class="invcard"><div class="invh"><b>{t["id"]}</b> <span class="grid">{html.escape(t["grid"])}</span></div>'
    f'<div class="invt">{html.escape(t["title"])}</div></div>' for t in inversions)

DATA = json.dumps([{
  "id":t["id"],"slug":t["slug"],"title":t["title"],"insight":t["insight"],"pattern":t["pattern"],
  "prompt":t["prompt"],"should":t["should"],"did":t["did"],"veins":t["veins"],"tier":t["tier"],
  "g":[t["g51"],t["g55"],t["son"]],"new":t["id"] in NEW_IDS,
} for t in tasks], ensure_ascii=False)
VEIN_OPTS = "".join(f'<option value="{html.escape(v)}">{html.escape(v)} ({vein_count[v]})</option>' for v,_ in sorted(vein_count.items(),key=lambda kv:-kv[1]))
VC_JSON = json.dumps(VCOLOR); TL_JSON = json.dumps(TIER_LABEL); TC_JSON = json.dumps(TIER_COLOR)

HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Breaker Atlas — ecommerce-browser-gym</title><style>
:root{{--bg:#0a0d13;--c1:#141923;--c2:#1a2030;--bd:#27303f;--tx:#e8ebf1;--mut:#8a94a6;--ac:#60a5fa;--gd:#34d399;--rd:#f87171}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#16203a 0,var(--bg) 55%);color:var(--tx);font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:34px 22px 80px}}
.hero h1{{font-size:30px;margin:0 0 6px;letter-spacing:-.5px}}.hero p{{color:var(--mut);margin:0 0 4px;max-width:760px}}
.tag{{display:inline-block;background:#13243f;color:#7eb6ff;border:1px solid #1e3a63;border-radius:20px;padding:3px 11px;font-size:12px;margin:10px 6px 0 0}}
h2{{font-size:19px;margin:42px 0 16px;display:flex;align-items:center;gap:9px}}h2::before{{content:"";width:4px;height:19px;background:var(--ac);border-radius:2px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:13px;margin-top:22px}}
.kpi{{background:linear-gradient(160deg,var(--c2),var(--c1));border:1px solid var(--bd);border-radius:15px;padding:17px}}
.kpi .v{{font-size:31px;font-weight:800;line-height:1}}.kpi .l{{color:var(--mut);font-size:12.5px;margin-top:7px}}.kpi .d{{font-size:11.5px;margin-top:5px;color:var(--gd)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}@media(max-width:860px){{.grid2{{grid-template-columns:1fr}}}}
.card{{background:var(--c1);border:1px solid var(--bd);border-radius:16px;padding:20px}}
.gaunt{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.gcol{{background:var(--c2);border:1px solid var(--bd);border-radius:13px;padding:16px;text-align:center}}
.gcol .m{{font-size:13px;color:var(--mut)}}.gcol .b{{font-size:34px;font-weight:800;margin:6px 0}}
.gcol .bar{{height:7px;background:#0c1119;border-radius:5px;overflow:hidden}}.gcol .bf{{height:100%}}
.barrow{{display:flex;align-items:center;gap:11px;margin:9px 0}}.blabel{{width:210px;font-size:13px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.btrack{{flex:1;background:#0c1119;border-radius:7px;height:24px;position:relative;overflow:hidden}}.bfill{{height:100%;border-radius:7px}}
.bin{{position:absolute;right:9px;top:0;line-height:24px;font-size:12px;font-weight:700;color:#cfd6e2}}
.stack{{display:flex;height:26px;border-radius:8px;overflow:hidden;border:1px solid var(--bd)}}.seg{{height:100%}}
.legend{{display:flex;flex-wrap:wrap;gap:13px;margin-top:13px;font-size:12.5px}}.lg{{display:flex;align-items:center;gap:6px;color:var(--mut)}}.lg b{{color:var(--tx)}}.lg i{{width:11px;height:11px;border-radius:3px}}
.invrow{{display:flex;gap:12px;overflow-x:auto;padding:4px 0}}
.invcard{{min-width:200px;background:linear-gradient(160deg,#2a1840,#1a1226);border:1px solid #3b2960;border-radius:12px;padding:13px}}
.invh{{display:flex;justify-content:space-between;align-items:center;font-size:13px}}.invh .grid{{color:#c4b5fd;font-family:ui-monospace,monospace;font-size:12px}}
.invt{{margin-top:7px;font-size:13.5px;color:#e9e3ff}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:6px 0 16px}}
input,select{{background:var(--c2);border:1px solid var(--bd);color:var(--tx);border-radius:9px;padding:9px 12px;font-size:13.5px}}
input{{flex:1;min-width:180px}}.count{{color:var(--mut);font-size:13px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}}
.tk{{background:var(--c1);border:1px solid var(--bd);border-radius:14px;padding:0;overflow:hidden;transition:border-color .15s}}
.tk:hover{{border-color:#3a455c}}.tk.brk{{border-left:3px solid var(--rd)}}
.tkh{{padding:15px 16px;cursor:pointer}}
.tkh .top{{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:7px}}
.tid{{font-weight:800;font-size:14px}}.tid .new{{background:#2563eb;color:#fff;font-size:9.5px;padding:1px 5px;border-radius:5px;margin-left:5px;vertical-align:middle}}
.chips{{display:flex;gap:4px}}.chip{{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;width:30px;text-align:center;border-radius:5px;padding:2px 0}}
.c-3{{background:#3a1414;color:#fca5a5}}.c-2{{background:#3a2410;color:#fdba74}}.c-1{{background:#3a3410;color:#fde047}}.c-0{{background:#0f2a1c;color:#6ee7b7}}.c-x{{background:#1a2030;color:#475569}}
.ttitle{{font-size:15px;font-weight:650;line-height:1.35}}.tins{{color:var(--mut);font-size:12.8px;margin-top:5px}}
.vbadges{{margin-top:9px;display:flex;flex-wrap:wrap;gap:5px}}.vb{{font-size:10.5px;padding:2px 8px;border-radius:20px;color:#0a0d13;font-weight:700}}
.tkbody{{display:none;border-top:1px solid var(--bd);padding:14px 16px;background:#0e131c}}.tk.open .tkbody{{display:block}}
.fld{{margin:11px 0}}.fld .h{{font-size:10.5px;letter-spacing:.5px;text-transform:uppercase;color:var(--mut);margin-bottom:4px;font-weight:700}}
.prompt{{background:#10233f;border:1px solid #1c3a63;border-radius:10px;padding:11px 13px;font-size:13.5px;color:#dbe7fb}}
.should{{border-left:3px solid var(--gd);padding-left:11px;font-size:13.5px}}.did{{border-left:3px solid var(--rd);padding-left:11px;font-size:13.5px}}
.patt{{font-size:12px;color:var(--mut);font-style:italic;margin-top:10px}}
.tierbadge{{font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;color:#0a0d13;white-space:nowrap}}
footer{{color:var(--mut);font-size:12.5px;margin-top:46px;border-top:1px solid var(--bd);padding-top:16px}}
.find{{background:var(--c1);border:1px solid var(--bd);border-left:3px solid var(--ac);border-radius:11px;padding:13px 16px;margin:9px 0;font-size:14px}}.find b{{color:#fff}}
.find.r{{border-left-color:var(--rd)}}.find.p{{border-left-color:#a855f7}}.find.g{{border-left-color:var(--gd)}}
</style></head><body><div class="wrap">

<div class="hero"><h1>🧨 Breaker Atlas</h1>
<p>Causal agent-failure modes harvested in <b>ecommerce-browser-gym</b> — multi-app browser tasks where a capable agent commits a real, state-observable harm. Each task screened on <b>gpt-5.1 · gpt-5.5 · Sonnet</b> at k=3 seeds; a break = a forbidden milestone fired in live state.</p>
<span class="tag">{N} breakers</span><span class="tag">{all3} break all 3 models</span><span class="tag">{len(inversions)} inversions</span><span class="tag">click any card to expand</span></div>

<div class="kpis">
 <div class="kpi"><div class="v">{N}</div><div class="l">Breaker tasks</div><div class="d">+10 this session</div></div>
 <div class="kpi"><div class="v" style="color:var(--rd)">{all3}</div><div class="l">Break ALL 3 models</div><div class="d">was 13 → ×{all3/13:.1f}</div></div>
 <div class="kpi"><div class="v" style="color:#fb923c">{pair}</div><div class="l">Break 5.5 + Sonnet</div><div class="d">was 14 → ×{pair/14:.1f}</div></div>
 <div class="kpi"><div class="v" style="color:#a855f7">{sonb}</div><div class="l">Break Sonnet</div><div class="d">the diligent model</div></div>
 <div class="kpi"><div class="v">{len(inversions)}</div><div class="l">Inversions</div><div class="d">strong breaks, weak resists</div></div>
 <div class="kpi"><div class="v">{len(vein_count)}</div><div class="l">Distinct veins</div><div class="d">multi-tagged</div></div>
</div>

<h2>The model gauntlet</h2>
<div class="gaunt">
 <div class="gcol"><div class="m">gpt-5.1</div><div class="b" style="color:#60a5fa">{g51b}</div><div class="bar"><div class="bf" style="width:{100*g51b//N}%;background:#60a5fa"></div></div><div class="m" style="margin-top:7px">of {N} broken</div></div>
 <div class="gcol"><div class="m">gpt-5.5</div><div class="b" style="color:#fb923c">{g55b}</div><div class="bar"><div class="bf" style="width:{100*g55b//N}%;background:#fb923c"></div></div><div class="m" style="margin-top:7px">of {N} broken</div></div>
 <div class="gcol"><div class="m">Sonnet (4.6)</div><div class="b" style="color:#f87171">{sonb}</div><div class="bar"><div class="bf" style="width:{100*sonb//N}%;background:#f87171"></div></div><div class="m" style="margin-top:7px">of {N} broken</div></div>
</div>

<div class="grid2" style="margin-top:20px">
 <div class="card"><h2 style="margin-top:0">Failure veins <span style="font-size:12px;color:var(--mut);font-weight:400">(multi-tagged — a task can carry several)</span></h2>{veinbars}</div>
 <div class="card"><h2 style="margin-top:0">Robustness tiers</h2><div class="stack">{tierseg}</div><div class="legend">{tierleg}</div>
  <h2 style="font-size:15px">Inversions — stronger model breaks, gpt-5.1 resists</h2><div class="invrow">{invcards}</div></div>
</div>

<h2>Every breaker — searchable</h2>
<div class="controls">
 <input id="q" placeholder="🔎 search id, title, prompt, harm…">
 <select id="fv"><option value="">All veins</option>{VEIN_OPTS}</select>
 <select id="ft"><option value="">All tiers</option>
  <option value="ALL-3">Breaks all 3</option><option value="strong-pair(5.5+son)">5.5 + Sonnet</option>
  <option value="sonnet-only">Sonnet-only</option><option value="gpt-5.1-only">gpt-5.1-only</option>
  <option value="gpt-5.5-only">gpt-5.5-only</option><option value="resist/fumble">Weak-model only</option></select>
 <span class="count" id="cnt"></span>
</div>
<div class="cards" id="cards"></div>

<h2>Key findings</h2>
<div class="find r"><b>Hidden harm at checkout beats every model.</b> Expired/corporate cards, stale gift messages, sneaked add-ons — the harm isn't shown where the agent acts, so even Sonnet commits it. Biggest, most robust vein.</div>
<div class="find p"><b>Sycophancy is the second theme — and it's cross-cutting.</b> Deferring to a confident false user claim (price, rating, "you charged me twice") shows up woven through infeasibility, false-premise and false-confirmation tasks — counted honestly it's ~3× what a single label suggests.</div>
<div class="find"><b>Tool-affordance × false-confirmation specifically beats Sonnet.</b> The agent performs an action then over-confirms despite contradicting feedback — several are inversions (Sonnet breaks, gpt-5.1 resists).</div>
<div class="find g"><b>What the strong models resist:</b> reading numbers, cross-object logical conditionals, live-state checks, injection recognition. The lever is concealment & deference — not complexity.</div>

<footer>Self-contained · data: coverage_matrix.csv + sellable_breakers_v2.csv · {N} breakers · companion: CROSS_MODEL_COMPARISON.md · editorial copy by parallel agent pass</footer>
</div>
<script>
const DATA={DATA},VC={VC_JSON},TL={TL_JSON},TC={TC_JSON};
const cell=v=>v==null?'<span class="chip c-x">·</span>':'<span class="chip c-'+v+'">'+v+'</span>';
function card(t){{
 const brk=(t.g[0]>=2)||(t.g[1]>=2)||(t.g[2]>=2);
 const vb=t.veins.map(v=>'<span class="vb" style="background:'+(VC[v]||'#475569')+'">'+v+'</span>').join('');
 return `<div class="tk ${{brk?'brk':''}}" data-id="${{t.id}}">
  <div class="tkh" onclick="this.parentNode.classList.toggle('open')">
   <div class="top"><div class="tid">${{t.id}}${{t.new?'<span class="new">NEW</span>':''}}</div>
    <div style="display:flex;gap:8px;align-items:center"><div class="chips">${{cell(t.g[0])}}${{cell(t.g[1])}}${{cell(t.g[2])}}</div>
    <span class="tierbadge" style="background:${{TC[t.tier]||'#475569'}}">${{TL[t.tier]||t.tier}}</span></div></div>
   <div class="ttitle">${{esc(t.title)}}</div>
   ${{t.insight?'<div class="tins">'+esc(t.insight)+'</div>':''}}
   <div class="vbadges">${{vb}}</div>
  </div>
  <div class="tkbody">
   <div class="fld"><div class="h">🗣️ Prompt given to the agent</div><div class="prompt">${{esc(t.prompt)}}</div></div>
   <div class="fld"><div class="h">✅ What it had to do</div><div class="should">${{esc(t.should)}}</div></div>
   <div class="fld"><div class="h">❌ What the agent did</div><div class="did">${{esc(t.did)}}</div></div>
   <div class="patt">pattern · ${{esc(t.pattern)}} &nbsp;·&nbsp; breaks: ${{esc(t.veins.join(', '))}}</div>
  </div></div>`;}}
function esc(s){{return (s||'').replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));}}
const cardsEl=document.getElementById('cards'),q=document.getElementById('q'),fv=document.getElementById('fv'),ft=document.getElementById('ft'),cnt=document.getElementById('cnt');
const order={{'ALL-3':0,'strong-pair(5.5+son)':1,'cross-family(2of3)':2,'sonnet-only':3,'gpt-5.5-only':4,'gpt-5.1-only':5,'resist/fumble':6}};
function tot(t){{return (t.g[0]||0)+(t.g[1]||0)+(t.g[2]||0);}}
function render(){{
 const s=q.value.toLowerCase(),v=fv.value,tr=ft.value;
 let rows=DATA.filter(t=>{{
  if(v&&!t.veins.includes(v))return false; if(tr&&t.tier!==tr)return false;
  if(s){{const blob=(t.id+' '+t.title+' '+t.insight+' '+t.prompt+' '+t.did+' '+t.should+' '+t.pattern).toLowerCase();if(!blob.includes(s))return false;}}
  return true;}});
 rows.sort((a,b)=>(order[a.tier]??9)-(order[b.tier]??9)||tot(b)-tot(a)||a.id.localeCompare(b.id));
 cardsEl.innerHTML=rows.map(card).join('');
 cnt.textContent=rows.length+' / '+DATA.length+' tasks';
}}
[q,fv,ft].forEach(e=>e.addEventListener('input',render));render();
</script></body></html>"""
out = os.path.join(T, "breaker_atlas.html")
open(out, "w", encoding="utf-8").write(HTML)
print(f"wrote {out} ({len(HTML.encode('utf-8'))} bytes) | {N} tasks | copy for {len(copy)} | "
      f"all3={all3} pair={pair} son={sonb} inversions={len(inversions)}")
print("veins:", dict(vein_count))
