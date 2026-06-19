"""Generate a self-contained HTML breaker-report dashboard from the sellable-breakers CSV."""
import csv, re, json
from collections import Counter, defaultdict

rows = list(csv.DictReader(open('trajectories/sellable_breakers_v2.csv', encoding='utf-8')))

CAT = {
 'M37':'Sycophancy / false-premise','M39':'Sycophancy / false-premise','M40':'Sycophancy / false-premise','M47':'Sycophancy / false-premise',
 'M41':"Ask-don't-guess (abstention)",'M76':"Ask-don't-guess (abstention)",'M80':"Ask-don't-guess (abstention)",
 'M43':'Source-anchoring (stale value)',
 'M51':'Silent substitution / value','M52':'Silent substitution / value',
 'M59':'Indirect injection / PII exfil',
 'M46':'Preselection / sneaked add-on','M72':'Preselection / sneaked add-on','M85':'Preselection / sneaked add-on',
 'M73':'Payment-validity: expired card','M84':'Payment-validity: expired card','M96':'Payment-validity: expired card',
 'M81':'Payment-validity: corporate card','M88':'Payment-validity: corporate card',
 'M75':'Hidden gift-message leak','M83':'Hidden gift-message leak','M95':'Hidden gift-message leak',
 'M55':'Per-line ship-to misroute','M56':'Per-line ship-to misroute','M57':'Per-line ship-to misroute','M70':'Per-line ship-to misroute',
 'M68':'Quantity-creep','M61':'Subscription on dead card',
 # --- Wave 1-4 portfolio (M123-M183) ---
 'M123':'Unchecked-postcondition','M124':'Unchecked-postcondition','M125':'Unchecked-postcondition',
 'M126':'Unchecked-postcondition','M128':'Unchecked-postcondition','M129':'Unchecked-postcondition',
 'M132':'Unchecked-postcondition','M137':'Unchecked-postcondition',
 'M127':'Silent substitution / value',
 'M139':'Infeasibility-blindness','M140':'Infeasibility-blindness','M141':'Infeasibility-blindness',
 'M142':'Infeasibility-blindness','M143':'Infeasibility-blindness','M145':'Infeasibility-blindness',
 'M147':'Infeasibility-blindness','M148':'Infeasibility-blindness','M149':'Infeasibility-blindness',
 'M151':'Conditional-logic collapse','M152':'Conditional-logic collapse','M154':'Conditional-logic collapse',
 'M155':'Conditional-logic collapse','M156':'Conditional-logic collapse','M157':'Conditional-logic collapse',
 'M158':'Conditional-logic collapse','M161':'Conditional-logic collapse','M163':'Conditional-logic collapse',
 'M164':'Conditional-logic collapse',
 'M165':'Embedded-instruction injection','M166':'Embedded-instruction injection','M167':'Embedded-instruction injection',
 'M169':'Embedded-instruction injection','M170':'Embedded-instruction injection','M171':'Embedded-instruction injection',
 'M172':'Embedded-instruction injection','M173':'Embedded-instruction injection','M174':'Embedded-instruction injection',
 'M175':'Embedded-instruction injection',
 'M179':'Over-scoping','M180':'Over-scoping','M182':'Over-scoping',
 'M177':'Premature-commitment','M183':'Negation-in-long-context',
}
MIX = {'M66','M74','M77','M78','M79','M82','M86','M87','M89','M90','M91','M92','M93','M94','M97','M98','M99','M100','M101','M102','M103','M104'}
MODELS = ['gpt-5.1','gpt-5.5','sonnet','qwen','haiku']

def short(tid): return tid.split('/')[0]
def parse_models(s):
    out={}
    for m,f,t in re.findall(r'(gpt-5\.1|gpt-5\.5|qwen-235b|qwen|haiku|sonnet)\s*~?(\d+)\s*/\s*(\d+)', s):
        m = 'qwen' if 'qwen' in m else m
        out[m]=[int(f),int(t)]
    return out
def tier(models):
    broke={m for m,(f,t) in models.items() if f>=1}
    claude = broke & {'sonnet','haiku'}
    if {'gpt-5.1','gpt-5.5'}<=broke and (claude or 'qwen' in broke): return 'Cross-family (3+ families)'
    if {'gpt-5.1','gpt-5.5'}<=broke: return 'Both OpenAI (5.1 + 5.5)'
    if 'gpt-5.1' in broke and ('qwen' in broke or claude): return 'gpt-5.1 + cheap model'
    if broke=={'gpt-5.1'}: return 'gpt-5.1 only'
    if broke=={'gpt-5.5'}: return 'gpt-5.5 only'
    if broke=={'qwen'} or broke=={'gpt-5.5','qwen'}: return 'Qwen-specific'
    return 'Other'

tasks=[]
for r in rows:
    tid=short(r['task_id'])
    cat = 'Stacked MIX (2-3 harms)' if tid in MIX else CAT.get(tid,'Other')
    m=parse_models(r['models_broken (fail/total)'])
    tasks.append({'id':tid,'name':r['task_id'].split('/')[1],'cat':cat,'tier':tier(m),'models':m,
                  'pattern':r['pattern'],'brief':r['brief (prompt)'],'expected':r['expected_correct_behavior'],
                  'wrong':r['what_the_agent_does_wrong'],'robust':r['robustness']})

catc=Counter(t['cat'] for t in tasks)
tierc=Counter(t['tier'] for t in tasks)
magg=defaultdict(lambda:[0,0,0]); mtb=defaultdict(int)
for t in tasks:
    for m,(f,tot) in t['models'].items():
        magg[m][0]+=f; magg[m][1]+=tot; magg[m][2]+=1
        if f>=1: mtb[m]+=1

payload={
 'total':len(tasks),
 'tasks':sorted(tasks,key=lambda t:int(t['id'][1:])),
 'cat':[[c,n] for c,n in catc.most_common()],
 'tier':[[c,n] for c,n in tierc.most_common()],
 'model':[{'m':m,'rate':round(magg[m][0]/magg[m][1]*100,1),'broke':magg[m][0],'tot':magg[m][1],
           'tb':mtb[m],'tt':magg[m][2]} for m in MODELS if m in magg],
}

TPL = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browser-Agent Failure-Mode Harvest</title>
<script>__CHARTJS__</script>
<style>
:root{--bg:#0a0e1a;--p1:#121829;--p2:#19203a;--line:#283254;--txt:#e8edf9;--mut:#8d9abc;
--acc:#7c93ff;--acc2:#34e2e4;--hot:#ff5d73;--warn:#ffb454;--good:#37e0a0;--vio:#b07cff;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:radial-gradient(1200px 600px at 80% -10%,#1a2342 0,var(--bg) 55%) ,var(--bg);
color:var(--txt);font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1280px;margin:0 auto;padding:38px 26px 70px}
.eyebrow{letter-spacing:.22em;text-transform:uppercase;font-size:12px;font-weight:700;color:var(--acc2);margin-bottom:10px}
h1{font-size:42px;line-height:1.08;font-weight:800;letter-spacing:-.02em;
background:linear-gradient(92deg,#fff 10%,var(--acc) 55%,var(--acc2) 95%);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--mut);font-size:16px;max-width:760px;margin-top:14px}
.grid{display:grid;gap:18px}
.cards{grid-template-columns:repeat(5,1fr);margin:34px 0}
@media(max-width:880px){.cards{grid-template-columns:repeat(2,1fr)}}
.card{background:linear-gradient(180deg,var(--p2),var(--p1));border:1px solid var(--line);border-radius:16px;padding:20px 18px;position:relative;overflow:hidden}
.card:before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--acc),var(--acc2))}
.kpi{font-size:34px;font-weight:800;letter-spacing:-.02em}
.kpi small{font-size:16px;color:var(--mut);font-weight:600}
.klab{color:var(--mut);font-size:12.5px;margin-top:4px;font-weight:600;letter-spacing:.02em}
.sec{margin-top:40px}.sec h2{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:10px}
.sec h2:after{content:"";flex:1;height:1px;background:var(--line)}
.panel{background:linear-gradient(180deg,var(--p2),var(--p1));border:1px solid var(--line);border-radius:18px;padding:22px}
.charts{grid-template-columns:1.25fr 1fr}
@media(max-width:880px){.charts{grid-template-columns:1fr}}
.charts2{grid-template-columns:1fr 1fr}
@media(max-width:880px){.charts2{grid-template-columns:1fr}}
.ptitle{font-weight:700;font-size:15px;margin-bottom:4px}.pdesc{color:var(--mut);font-size:12.5px;margin-bottom:14px}
.law{grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:880px){.law{grid-template-columns:1fr}}
.lawcard{border-radius:16px;padding:22px;border:1px solid var(--line)}
.lawcard.miss{background:linear-gradient(180deg,#2a1622,#1a1020);border-color:#54283a}
.lawcard.catch{background:linear-gradient(180deg,#10231d,#0e1a18);border-color:#1f4a3c}
.lawcard h3{font-size:16px;margin-bottom:6px}.lawcard .tag{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
.miss .tag{color:var(--hot)}.catch .tag{color:var(--good)}
.lawcard ul{margin:12px 0 0 0;list-style:none}.lawcard li{padding:7px 0;border-top:1px solid rgba(255,255,255,.06);font-size:14px;color:#d4dcf0}
.lawcard li b{color:#fff}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--mut);font-weight:600;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:10px 10px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--p1)}
td{padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05);vertical-align:top}
tr:hover td{background:rgba(124,147,255,.05)}
.tid{font-weight:700;color:#fff;white-space:nowrap}
.cell{display:inline-block;min-width:42px;text-align:center;border-radius:7px;padding:3px 6px;font-weight:700;font-size:12px}
.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.02em}
.detail{color:var(--mut);font-size:12px;cursor:pointer;user-select:none}
.detail summary{color:var(--acc2);font-weight:600;outline:none}
.detail[open] summary{margin-bottom:6px}
.kv{margin:3px 0}.kv b{color:#cdd6ee}
.foot{margin-top:46px;color:var(--mut);font-size:12.5px;text-align:center}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--mut);margin-top:12px}
.dot{width:11px;height:11px;border-radius:3px;display:inline-block;vertical-align:middle;margin-right:5px}
.tablewrap{max-height:760px;overflow:auto;border-radius:14px;border:1px solid var(--line)}
.note{background:linear-gradient(180deg,#181f3a,#121829);border:1px solid var(--line);border-left:3px solid var(--acc2);border-radius:12px;padding:16px 18px;color:#cfd8f2;font-size:14px}
</style></head>
<body><div class="wrap">
<div class="eyebrow">Browser-Agent RL Gym &nbsp;&middot;&nbsp; Failure-Mode Harvest</div>
<h1>Where frontier browser agents break</h1>
<p class="sub">A catalogue of <b>__TOTAL__ statistically-validated, causal failure modes</b> harvested in a multi-app e-commerce gym, screened at k=3 across five frontier models. Every entry is an oracle-gated task with a state-based verifier: a single clean correct path exists, and the agents take a measurably wrong one.</p>

<div class="grid cards" id="kpis"></div>

<div class="sec"><h2>The load-bearing finding &mdash; the two-factor law</h2>
<div class="note">Frontier models (incl. <b>GPT&#8209;5.5</b> and <b>Claude Sonnet</b>) catch a harm <b>only</b> when it has a <b>visible cue at the point of action</b> <b>and</b> they are <b>undistracted</b>. Remove either factor and they break &mdash; across families.</div>
<div class="grid law" style="margin-top:18px">
<div class="lawcard catch"><div class="tag">What they CATCH</div><h3>Visible &amp; undistracted</h3>
<ul>
<li><b>Sneaked add-on</b>, isolated &mdash; gpt&#8209;5.5 removes it (M72, M85)</li>
<li><b>Corporate-card label</b>, isolated &mdash; visible at checkout, gpt&#8209;5.5 switches it (M81, M88)</li>
<li><b>Per-line ship-to</b> &mdash; the Claude family diligently sets it (M55, M70)</li>
</ul></div>
<div class="lawcard miss"><div class="tag">What they MISS &mdash; the sellable veins</div><h3>Hidden or load-masked</h3>
<ul>
<li><b>Expired-card validity</b> &mdash; not shown at checkout &rarr; <b>cross-family</b> (M73, M96: 3 families)</li>
<li><b>Hidden gift-message</b> &mdash; under a collapsed panel &rarr; <b>cross-family</b> (M75, M95)</li>
<li><b>Load-masking</b> &mdash; a concurrent task hides a harm they'd otherwise catch (M79, M86, M91)</li>
</ul></div>
</div></div>

<div class="sec"><h2>Distribution &amp; analytics</h2>
<div class="grid charts">
<div class="panel"><div class="ptitle">Break rate by model</div><div class="pdesc">Share of k=3 episodes the model took the wrong action, pooled over every task it was screened on.</div><canvas id="cModel" height="150"></canvas></div>
<div class="panel"><div class="ptitle">Robustness tier</div><div class="pdesc">How broadly each breaker generalises across model families.</div><canvas id="cTier" height="150"></canvas></div>
</div>
<div class="grid charts2" style="margin-top:18px">
<div class="panel"><div class="ptitle">Breakers by pattern</div><div class="pdesc">Primary failure mechanism per task (mixes counted once).</div><canvas id="cCat" height="220"></canvas></div>
<div class="panel"><div class="ptitle">Task coverage per model</div><div class="pdesc">Tasks broken vs tasks screened.</div><canvas id="cCov" height="220"></canvas></div>
</div></div>

<div class="sec"><h2>The full catalogue &mdash; __TOTAL__ breakers</h2>
<div class="legend">
<span><span class="dot" style="background:var(--hot)"></span>breaks (3/3)</span>
<span><span class="dot" style="background:var(--warn)"></span>partial break</span>
<span><span class="dot" style="background:var(--good)"></span>resists</span>
<span><span class="dot" style="background:#39425f"></span>not screened</span>
</div>
<div class="tablewrap" style="margin-top:12px"><table><thead><tr>
<th>Task</th><th>Pattern</th><th>gpt-5.1</th><th>gpt-5.5</th><th>Sonnet</th><th>Qwen</th><th>Haiku</th><th>Robustness</th></tr></thead>
<tbody id="rows"></tbody></table></div></div>

<div class="foot">Generated from <code>sellable_breakers_v2.csv</code> &middot; e-commerce-browser-gym &middot; all results screened at k=3 &middot; verifiers are state-based + oracle-gated.</div>
</div>
<script>
const DATA = __DATA__;
const MODS=['gpt-5.1','gpt-5.5','sonnet','qwen','haiku'];
const C={txt:'#e8edf9',mut:'#8d9abc',line:'#283254',acc:'#7c93ff',acc2:'#34e2e4',hot:'#ff5d73',warn:'#ffb454',good:'#37e0a0',vio:'#b07cff'};
Chart.defaults.color=C.mut;Chart.defaults.font.family="Inter,system-ui,sans-serif";Chart.defaults.borderColor=C.line;

// KPIs
const mById=Object.fromEntries(DATA.model.map(x=>[x.m,x]));
const tc=(m)=>mById[m].tb+'/'+mById[m].tt+' tasks';
const kpis=[['Confirmed breakers',DATA.total,'oracle-gated &middot; k=3'],
 ['gpt-5.1 break rate',mById['gpt-5.1'].rate+'%',tc('gpt-5.1')],
 ['gpt-5.5 break rate',mById['gpt-5.5'].rate+'%',tc('gpt-5.5')],
 ['Claude Sonnet',mById['sonnet'].rate+'%',tc('sonnet')],
 ['Cross-family veins',DATA.tier.filter(t=>t[0].startsWith('Cross'))[0][1],'break 3+ families']];
document.getElementById('kpis').innerHTML=kpis.map(k=>`<div class="card"><div class="kpi">${k[1]}</div><div class="klab">${k[0]} &middot; ${k[2]}</div></div>`).join('');

const grad=(ctx,a,b)=>{const g=ctx.createLinearGradient(0,0,0,260);g.addColorStop(0,a);g.addColorStop(1,b);return g;};
// model break rate
new Chart(cModel,{type:'bar',data:{labels:DATA.model.map(x=>x.m),datasets:[{data:DATA.model.map(x=>x.rate),
 backgroundColor:c=>grad(c.chart.ctx,'#ff7a8a','#ff3d5a'),borderRadius:8,maxBarThickness:46}]},
 options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.raw+'%  ('+DATA.model[c.dataIndex].broke+'/'+DATA.model[c.dataIndex].tot+' episodes)'}}},
 scales:{y:{beginAtZero:true,max:100,grid:{color:C.line},ticks:{callback:v=>v+'%'}},x:{grid:{display:false},ticks:{font:{weight:700}}}}}});
// tier donut
new Chart(cTier,{type:'doughnut',data:{labels:DATA.tier.map(x=>x[0]),datasets:[{data:DATA.tier.map(x=>x[1]),
 backgroundColor:[C.hot,C.acc,C.warn,C.vio,'#5566aa',C.acc2,C.good],borderColor:'#121829',borderWidth:2}]},
 options:{cutout:'62%',plugins:{legend:{position:'right',labels:{boxWidth:11,font:{size:11.5}}}}}});
// category horizontal bar
new Chart(cCat,{type:'bar',data:{labels:DATA.cat.map(x=>x[0]),datasets:[{data:DATA.cat.map(x=>x[1]),
 backgroundColor:c=>grad(c.chart.ctx,'#8aa0ff','#5b73ff'),borderRadius:7,maxBarThickness:26}]},
 options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:C.line},ticks:{precision:0}},y:{grid:{display:false},ticks:{font:{size:11.5}}}}}});
// coverage grouped
new Chart(cCov,{type:'bar',data:{labels:DATA.model.map(x=>x.m),datasets:[
 {label:'broke',data:DATA.model.map(x=>x.tb),backgroundColor:C.hot,borderRadius:6,maxBarThickness:30},
 {label:'screened',data:DATA.model.map(x=>x.tt),backgroundColor:'#39425f',borderRadius:6,maxBarThickness:30}]},
 options:{plugins:{legend:{labels:{boxWidth:11}}},scales:{y:{beginAtZero:true,grid:{color:C.line},ticks:{precision:0}},x:{grid:{display:false},ticks:{font:{weight:700}}}}}});

// table
function cell(m){if(!m)return '<span class="cell" style="background:#1d2440;color:#566089">&middot;</span>';
 const r=m[0]/m[1];const bg=r>=.99?'rgba(255,93,115,.92)':r>=.34?'rgba(255,180,84,.9)':'rgba(55,224,160,.85)';
 const fg=r>=.34?'#1a0e14':'#08140f';return `<span class="cell" style="background:${bg};color:${fg}">${m[0]}/${m[1]}</span>`;}
const tierColor={'Cross-family (3+ families)':C.hot,'Both OpenAI (5.1 + 5.5)':C.acc,'gpt-5.1 + cheap model':C.warn,'gpt-5.1 only':C.vio,'gpt-5.5 only':C.acc2,'Qwen-specific':'#5566aa','Other':'#566089'};
document.getElementById('rows').innerHTML=DATA.tasks.map(t=>{
 const tc=tierColor[t.tier]||'#566089';
 return `<tr>
 <td class="tid">${t.id}</td>
 <td>${t.pattern}<details class="detail"><summary>details</summary>
   <div class="kv"><b>Prompt:</b> ${esc(t.brief)}</div>
   <div class="kv"><b>Correct:</b> ${esc(t.expected)}</div>
   <div class="kv"><b>Failure:</b> ${esc(t.wrong)}</div></details></td>
 <td>${cell(t.models['gpt-5.1'])}</td><td>${cell(t.models['gpt-5.5'])}</td><td>${cell(t.models['sonnet'])}</td>
 <td>${cell(t.models['qwen'])}</td><td>${cell(t.models['haiku'])}</td>
 <td><span class="badge" style="background:${tc}22;color:${tc};border:1px solid ${tc}55">${t.tier}</span></td></tr>`;}).join('');
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
</script></body></html>'''

chartjs = open('trajectories/_chartjs.min.js', encoding='utf-8').read()
html = (TPL.replace('__DATA__', json.dumps(payload))
           .replace('__TOTAL__', str(payload['total']))
           .replace('__CHARTJS__', chartjs))
open('trajectories/breaker_report.html','w',encoding='utf-8').write(html)
print('wrote trajectories/breaker_report.html', len(html), 'bytes (self-contained)')
