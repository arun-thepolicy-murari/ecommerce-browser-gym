window.REPORT_DATA={failures:[
{label:'Stacked defaults',value:18},{label:'False-premise deference',value:15},{label:'Instrument defaults',value:11},{label:'Content defaults',value:10},{label:'Ambiguity resolution',value:8},{label:'Infeasibility',value:6},{label:'Tool-outcome verification',value:5},{label:'Contextual boundary inference',value:5},{label:'Cross-step state tracking',value:4},{label:'Structural / conditional',value:3}
]};
function renderBars(target,rows,total=85){const el=document.querySelector(target);if(!el)return;el.innerHTML=rows.map((row)=>{const pct=row.value/total*100;return `<div class="bar-row"><div class="bar-label"><span>${row.label}</span><b>${row.value}</b></div><div class="bar-track"><i style="--w:${pct}%"></i></div><small>${pct.toFixed(1)}%</small></div>`}).join('')}
renderBars('#failure-bars',window.REPORT_DATA.failures);
