
let state={games:[],selected:null,view:"all",tab:"prediction",mode:"demo"};

async function loadBoard(forceDemo=false){
  let payload=null;
  if(!forceDemo){
    try{
      const r=await fetch("/api/v1/week-board/2",{cache:"no-store"});
      if(r.ok){payload=await r.json();}
    }catch(e){}
  }
  if(!payload || !payload.games || payload.games.length===0){
    const r=await fetch("week2_board.json",{cache:"no-store"}); payload=await r.json();
  }
  state.games=payload.games||[]; state.mode=payload.mode||"demo";
  if(!state.selected && state.games[0]) state.selected=state.games[0].id;
  document.getElementById("modeText").textContent =
    (payload.mode==="live" ? "LIVE PIPELINE" : "OPERATIONAL DEMO") +
    (payload.message ? " • "+payload.message : "");
  render();
}

async function refreshWeek(){
  const b=document.getElementById("refreshBtn"); b.textContent="Refreshing..."; b.disabled=true;
  try{
    const r=await fetch("/api/v1/refresh-week/2026/2",{method:"POST"});
    if(!r.ok) throw new Error("Backend unavailable");
    const p=await r.json();
    state.games=p.games||[]; state.mode=p.mode||"demo"; state.selected=state.games[0]?.id||null;
    document.getElementById("modeText").textContent=(p.mode==="live"?"LIVE PIPELINE":"OPERATIONAL DEMO")+" • "+(p.message||"Refresh complete");
  }catch(e){
    document.getElementById("modeText").textContent="Static demo mode • Live refresh requires the included backend + API keys. Demo reloaded successfully.";
    await loadBoard(true);
  }finally{b.textContent="Refresh Week 2";b.disabled=false;render();}
}
document.getElementById("refreshBtn").onclick=refreshWeek;
document.getElementById("demoBtn").onclick=()=>loadBoard(true);

function filtered(){
 let a=[...state.games],q=document.getElementById("search").value.toLowerCase();
 if(q)a=a.filter(g=>(g.away+" "+g.home).toLowerCase().includes(q));
 if(state.view==="edges")a=a.filter(g=>Math.abs(g.decision?.edge||0)>=2.5);
 if(state.view==="qualified")a=a.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state));
 if(state.view==="fails")a=a.filter(g=>g.decision?.state==="FAIL");
 if(state.view==="results")a=a.filter(g=>g.result);
 let s=document.getElementById("sort").value;
 a.sort((x,y)=>s==="dqs"?(y.derived?.dqs||0)-(x.derived?.dqs||0):s==="ocrs"?(x.derived?.ocrs||0)-(y.derived?.ocrs||0):Math.abs(y.decision?.edge||0)-Math.abs(x.decision?.edge||0));
 return a;
}
function render(){
 const a=filtered(),qs=state.games.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state)).length,fs=state.games.filter(g=>g.decision?.state==="FAIL").length;
 document.getElementById("summary").innerHTML=`<div class=chip><b>${state.games.length}</b><span>Games</span></div><div class=chip><b>${qs}</b><span>Qualified</span></div><div class=chip><b>${fs}</b><span>Fails</span></div>`;
 document.getElementById("games").innerHTML=a.map(g=>`<div class="game ${g.id===state.selected?"active":""}" onclick="selectGame('${g.id}')"><div class=row><div><div class=match>${g.away} @ ${g.home}</div><div class=small>${g.market?.display||fmtMarket(g.market)}</div></div><span class="badge ${g.decision?.state}">${g.decision?.state||"NA"}</span></div><div class="row small" style="margin-top:8px"><span>Edge ${num(g.decision?.edge)}</span><span>DQS ${num(g.derived?.dqs)} • OCRS ${num(g.derived?.ocrs)}</span></div></div>`).join("");
 renderDetail();
}
function selectGame(id){state.selected=id;state.tab="prediction";render()}
function fmtMarket(m){if(!m)return"Market unavailable";return `${m.home_spread!=null?"Home "+m.home_spread:""} ${m.total!=null?" • O/U "+m.total:""}`.trim()||"Market unavailable"}
function num(x){return x==null?"—":Number(x).toFixed(1)}
function pct(x){return x==null?"—":(Number(x)*100).toFixed(1)+"%"}
function tab(id,label){return `<button class="tab ${state.tab===id?"active":""}" onclick="setTab('${id}')">${label}</button>`}
function setTab(x){state.tab=x;renderDetail()}
function renderDetail(){
 const g=state.games.find(x=>x.id===state.selected)||state.games[0]; if(!g){document.getElementById("detail").innerHTML="No game selected";return}
 const p=g.prediction||{},d=g.derived||{},ev=g.ev||{},dec=g.decision||{};
 document.getElementById("detail").innerHTML=`<div class=hero><div class=row><div><h2>${g.away} @ ${g.home}</h2><div class=small>${g.kickoff||""} ${g.venue?"• "+g.venue:""}</div></div><span class="badge ${dec.state}">${dec.state}</span></div>
 <div class=score>${num(p.away_points)} – ${num(p.home_points)}</div>
 <div class=metrics><div class=metric><span>Edge</span><b>${num(dec.edge)}</b></div><div class=metric><span>DQS</span><b>${num(d.dqs)}</b></div><div class=metric><span>OCRS</span><b>${num(d.ocrs)}</b></div><div class=metric><span>EV</span><b>${ev.expected_value==null?"—":(ev.expected_value*100).toFixed(1)+"%"}</b></div></div>
 <div class=tabs>${tab("prediction","Prediction")}${tab("market","Market Edge")}${tab("trench","Trench")}${tab("risk","Risk")}${tab("attr","Attribution")}${tab("quality","Data Quality")}${tab("raw","Raw")}</div>
 <div class=panel>${panel(g)}</div></div>`;
}
function panel(g){
 const p=g.prediction||{},d=g.derived||{},ev=g.ev||{},dec=g.decision||{};
 if(state.tab==="prediction")return `<div class=item><span>Projected score</span><b>${g.away} ${num(p.away_points)} • ${g.home} ${num(p.home_points)}</b></div><div class=item><span>Model total</span><b>${num(p.model_total)}</b></div><div class=item><span>Home margin</span><b>${num(p.model_margin_home)}</b></div><div class=item><span>Decision</span><b>${dec.state}</b></div><div class=item><span>Probability</span><b>${pct(ev.probability)}</b></div>`;
 if(state.tab==="market")return `<div class=item><span>Market</span><b>${g.market?.display||fmtMarket(g.market)}</b></div><div class=item><span>Spread edge</span><b>${num(p.spread_edge_home)}</b></div><div class=item><span>Total edge</span><b>${num(p.total_edge_over)}</b></div><div class=item><span>Break-even</span><b>${pct(ev.break_even_probability)}</b></div><div class=item><span>Expected value</span><b>${ev.expected_value==null?"—":(ev.expected_value*100).toFixed(2)+"%"}</b></div>`;
 if(state.tab==="trench")return `<div class=item><span>${g.away} RunMOTE</span><b>${num(g.trench?.away?.RunMOTE)}</b></div><div class=item><span>${g.away} PassMOTE</span><b>${num(g.trench?.away?.PassMOTE)}</b></div><div class=item><span>${g.home} RunMOTE</span><b>${num(g.trench?.home?.RunMOTE)}</b></div><div class=item><span>${g.home} PassMOTE</span><b>${num(g.trench?.home?.PassMOTE)}</b></div>`;
 if(state.tab==="risk")return `<div class=item><span>OCRS</span><b>${num(d.ocrs)}</b></div><div class=item><span>DFR</span><b>${num(d.dfr)}</b></div><div class=item><span>FPSE</span><b>${num(d.fpse)}</b></div>${(dec.reasons||[]).map(x=>`<div class=item><span>Gate note</span><b>${x}</b></div>`).join("")}`;
 if(state.tab==="attr"){let a=g.attribution||{};return `<h3>Drivers</h3>${(a.drivers||[]).map(x=>`<div class=item><span>${x.name}</span><b class=good>${x.contribution??""}</b></div>`).join("")}<h3>Counterweights</h3>${(a.counterweights||[]).map(x=>`<div class=item><span>${x.name}</span><b class=bad>${x.contribution??""}</b></div>`).join("")}<div class=item><span>ECS</span><b>${num(a.ecs)}</b></div><div class=item><span>DAC</span><b>${a.dac??"—"}</b></div>`}
 if(state.tab==="quality")return `<div class=item><span>Away reliability</span><b>${pct(g.quality?.away_reliability)}</b></div><div class=item><span>Home reliability</span><b>${pct(g.quality?.home_reliability)}</b></div><div class=item><span>DQS</span><b>${num(d.dqs)}</b></div><div class=item><span>Provider mode</span><b>${g.provider_meta?.mode||"demo"}</b></div>`;
 return `<pre>${escapeHtml(JSON.stringify(g,null,2))}</pre>`;
}
function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>{document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));b.classList.add("active");state.view=b.dataset.view;render()});
document.getElementById("search").oninput=render;document.getElementById("sort").onchange=render;
loadBoard(false);
