
const state={games:[],view:"all",division:"all",sort:"default",search:"",selected:null,tab:"overview"};
const $=id=>document.getElementById(id);
const fbs=new Set(["Alabama","Arizona","Arizona State","Arkansas","Auburn","BYU","Boise State","Boston College","California","Cincinnati","Clemson","Colorado","Duke","Florida","Georgia","Georgia Tech","Houston","Illinois","Indiana","Iowa","Iowa State","Kentucky","LSU","Louisville","Maryland","Miami (FL)","Michigan","Michigan State","Minnesota","Mississippi State","Missouri","NC State","Nebraska","Notre Dame","Ohio State","Oklahoma","Oklahoma State","Ole Miss","Oregon","Penn State","Pittsburgh","Rutgers","SMU","South Carolina","Syracuse","TCU","Tennessee","Texas","Texas A&M","Texas Tech","UCF","UCLA","USC","Utah","Virginia","Virginia Tech","Washington","West Virginia","Wisconsin"]);
const whole=x=>x==null?"—":Math.round(Number(x));
const one=x=>x==null?"—":Number(x).toFixed(1);
const pct=x=>x==null?"—":Math.round(Number(x)*100)+"%";
const div=t=>fbs.has(t)?"FBS":"FCS";
const gameDiv=g=>div(g.away)!==div(g.home)?"cross":div(g.away).toLowerCase();
function showPage(id){["landing","learn","app"].forEach(x=>$(x).classList.toggle("hidden",x!==id));}
function statusLabel(g){const s=g.decision?.state;return s==="PASS"||s==="QUALIFIED"?"QUALIFIED BET":s==="FAIL"?"PASS":"WAIT FOR DATA";}
function badgeClass(g){const s=g.decision?.state;return s==="PASS"||s==="QUALIFIED"?"qual":s==="FAIL"?"pass":"wait";}
function market(g){return g.market?.display||"Market pending";}
function preferred(g){return g.decision?.side||"No qualified wager";}
function riskWord(x){if(x==null)return"Pending";return x>=65?"High":x>=45?"Moderate":"Low";}
function qualityWord(x){if(x==null)return"Pending";return x>=80?"Strong":x>=65?"Usable":"Limited";}
function colors(g){return {away:g.branding?.away?.primary||"#e11d2e",home:g.branding?.home?.primary||"#fff"};}
function winProb(g){const m=Number(g.prediction?.model_margin_home);if(!Number.isFinite(m))return null;const h=1/(1+Math.exp(-.16*m));return {home:h,away:1-h};}
function missing(g){
 const a=[];if(g.market?.home_spread==null&&g.market?.total==null)a.push("live market line");
 if(g.derived?.dqs==null)a.push("data quality inputs");if(g.derived?.ocrs==null)a.push("risk inputs");
 if(g.trench?.away?.RunMOTE==null||g.trench?.home?.RunMOTE==null)a.push("run trench grades");
 if(g.trench?.away?.PassMOTE==null||g.trench?.home?.PassMOTE==null)a.push("pass trench grades");
 if(g.provider_meta?.weather===false)a.push("weather");if(g.provider_meta?.injuries===false)a.push("verified injuries");
 return [...new Set(a)];
}
function filtered(){
 let a=[...state.games];
 if(state.search)a=a.filter(g=>(g.away+" "+g.home).toLowerCase().includes(state.search));
 if(state.division!=="all")a=a.filter(g=>gameDiv(g)===state.division);
 if(state.view==="qualified")a=a.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state));
 if(state.view==="value")a=a.filter(g=>Math.abs(Number(g.decision?.edge||0))>=2.5);
 if(state.view==="fbs")a=a.filter(g=>gameDiv(g)==="fbs");if(state.view==="fcs")a=a.filter(g=>gameDiv(g)==="fcs");
 if(state.sort==="edge")a.sort((x,y)=>Math.abs(y.decision?.edge||0)-Math.abs(x.decision?.edge||0));
 if(state.sort==="dqs")a.sort((x,y)=>(y.derived?.dqs??-999)-(x.derived?.dqs??-999));
 if(state.sort==="risk")a.sort((x,y)=>(x.derived?.ocrs??999)-(y.derived?.ocrs??999));
 return a;
}
function tabButton(id,label){return `<button class="tab ${state.tab===id?"active":""}" data-tab="${id}">${label}</button>`;}
function analysisPanel(g){
 const p=g.prediction||{},d=g.derived||{},a=g.attribution||{},wp=winProb(g),c=colors(g);
 if(state.tab==="why"){const dr=a.drivers||[];return dr.length?dr.slice(0,4).map((x,i)=>`<div class=item><span>${i+1}. ${x.name}</span><b>Supports pick</b></div>`).join(""):'<div class=explain>Driver analysis will populate as the live feature package improves.</div>';}
 if(state.tab==="risk")return `<div class=explain>Risk measures how vulnerable this projection is to realistic game events.</div><div class=item><span>Overall game risk</span><b>${riskWord(d.ocrs)}</b></div><div class=item><span>Drive-stalling risk</span><b>${riskWord(d.dfr)}</b></div><div class=item><span>Field-position risk</span><b>${riskWord(d.fpse)}</b></div>`;
 if(state.tab==="advanced")return `<div class=item><span>Run trench matchup</span><b>${one(g.trench?.away?.RunMOTE)} / ${one(g.trench?.home?.RunMOTE)}</b></div><div class=item><span>Pass trench matchup</span><b>${one(g.trench?.away?.PassMOTE)} / ${one(g.trench?.home?.PassMOTE)}</b></div><div class=item><span>Data Quality Score</span><b>${one(d.dqs)}</b></div><div class=item><span>Context Risk Score</span><b>${one(d.ocrs)}</b></div>`;
 let chart="";if(wp){const hp=Math.round(wp.home*100),ap=100-hp;chart=`<div class=win-grid><div class=donut style="background:conic-gradient(${c.home} ${hp}%,${c.away} 0)"><b>${hp}%</b></div><div class=legend><div class=legend-row><span><i class=swatch style="background:${c.home}"></i>${g.home}</span><b>${hp}%</b></div><div class=legend-row><span><i class=swatch style="background:${c.away}"></i>${g.away}</span><b>${ap}%</b></div></div></div>`;}
 return `<div class=item><span>Projected score</span><b>${p.away_points==null?"Pending":`${g.away} ${whole(p.away_points)} • ${g.home} ${whole(p.home_points)}`}</b></div><div class=item><span>Current betting line</span><b>${market(g)}</b></div><div class=item><span>TE preferred wager</span><b>${preferred(g)}</b></div>${chart}`;
}
function analysis(g){
 const p=g.prediction||{},d=g.derived||{},m=missing(g);
 return `<div class=analysis><div class=projection>${p.away_points==null?"Projection pending":`${g.away} ${whole(p.away_points)} • ${g.home} ${whole(p.home_points)}`}</div>
 <div class=metrics><div class=metric><span>Bet win chance</span><b>${pct(g.ev?.probability)}</b></div><div class=metric><span>Betting value</span><b>${g.decision?.edge==null?"—":one(Math.abs(g.decision.edge))+" pts"}</b></div><div class=metric><span>Data quality</span><b>${qualityWord(d.dqs)}</b></div><div class=metric><span>Game risk</span><b>${riskWord(d.ocrs)}</b></div></div>
 <div class=waitbar><b>${m.length?`TE is still waiting on ${m.length} input${m.length===1?"":"s"}`:"Data package is complete enough to evaluate"}</b><div class=pills>${m.map(x=>`<span class=pill>${x}</span>`).join("")}</div></div>
 <div class=tabs>${tabButton("overview","Overview")}${tabButton("why","Why TE Likes It")}${tabButton("risk","Risk Factors")}${tabButton("advanced","Advanced")}</div><div class=panel>${analysisPanel(g)}</div></div>`;
}
function render(){
 const a=filtered();if(state.selected&&!a.some(g=>g.id===state.selected))state.selected=null;
 const q=state.games.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state)).length;
 $("summary").innerHTML=`<div class=summary-card><b>${state.games.length}</b><span>Games</span></div><div class=summary-card><b>${q}</b><span>Qualified</span></div><div class=summary-card><b>${state.games.length-q}</b><span>Pass / wait</span></div>`;
 $("gameList").innerHTML=a.map(g=>`<article class="game-card ${state.selected===g.id?"open":""}" data-id="${g.id}"><div class=game-summary><div class=row><div><div class=matchup>${g.away} @ ${g.home}</div><div class=small>${market(g)}</div></div><span class="badge ${badgeClass(g)}">${statusLabel(g)}</span></div><div class="row small" style="margin-top:8px"><span>${g.prediction?.away_points==null?"Analysis pending":`Projected ${g.away} ${whole(g.prediction.away_points)}, ${g.home} ${whole(g.prediction.home_points)}`}</span><span>${g.decision?.edge==null?"":one(Math.abs(g.decision.edge))+" pt value"}</span></div><div class=toggle-cue>${state.selected===g.id?"▲ Hide matchup analysis":"▼ Show matchup analysis"}</div></div>${state.selected===g.id?analysis(g):""}</article>`).join("")||'<div class=panel>No games match this filter.</div>';
 document.querySelectorAll(".game-summary").forEach(el=>el.onclick=()=>{const id=el.parentElement.dataset.id;state.selected=state.selected===id?null:id;state.tab="overview";render();});
 document.querySelectorAll(".tab").forEach(el=>el.onclick=e=>{e.stopPropagation();state.tab=el.dataset.tab;render();});
}
function helmet(team,g,side){const c=g.branding?.[side]?.primary||"#555",t=g.branding?.[side]?.secondary||"#fff",mark=team.split(/\s+/).map(x=>x[0]).join("").slice(0,3).toUpperCase();return `<svg class=helmet-svg viewBox="0 0 110 78"><path d="M14 46C13 24 26 8 49 5C71 2 88 10 94 27C96 34 95 42 91 50H72C69 58 61 63 51 63H28C18 60 14 54 14 46Z" fill="${c}" stroke="rgba(255,255,255,.35)" stroke-width="2"/><circle cx="66" cy="45" r="5" fill="#111"/><text x="46" y="37" text-anchor="middle" dominant-baseline="middle" font-size="13" font-weight="900" fill="${t}">${mark}</text><path d="M73 51C82 52 91 51 98 47M80 54H99C103 54 104 60 100 62H85M87 48V66M55 63L41 70H27" stroke="${t}" stroke-width="3" fill="none" stroke-linecap="round"/></svg>`;}
function kickoff(v){const d=new Date(v);return Number.isNaN(d.getTime())?String(v||"Kickoff TBA"):new Intl.DateTimeFormat("en-US",{timeZone:"America/Chicago",weekday:"short",hour:"numeric",minute:"2-digit"}).format(d)+" CT";}
function scoreCard(g){return `<div class=score-card><div class=score-meta><span>${kickoff(g.kickoff)}</span><span>${g.venue||"Venue TBA"}</span></div><div class=helmet-match><div class=team-side>${helmet(g.away,g,"away")}<b>${g.away}</b><div class=score>${g.away_score??"–"}</div></div><div class=vs>VS</div><div class=team-side>${helmet(g.home,g,"home")}<b>${g.home}</b><div class=score>${g.home_score??"–"}</div></div></div><div class=location><b>Game location:</b> ${g.venue?`This matchup is scheduled at ${g.venue}.`:"Venue information has not been published yet."}</div></div>`;}
function renderScores(games){$("scoreList").innerHTML=games.map(scoreCard).join("");}
function openScores(){$("scoreDrawer").classList.add("open");$("scrim").classList.add("open");$("scoreDrawer").setAttribute("aria-hidden","false");renderScores(state.games);$("scoreStatus").textContent=`${state.games.length} scheduled Week 2 games • live state overlays when available`;fetch("/api/v1/scoreboard/2",{cache:"no-store"}).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(j.games?.length)renderScores(j.games);$("scoreStatus").textContent="Live scoreboard updated";}).catch(()=>{});}
function closeScores(){$("scoreDrawer").classList.remove("open");$("scrim").classList.remove("open");$("scoreDrawer").setAttribute("aria-hidden","true");}
function merge(base,live){const m=new Map(base.map(g=>[`${g.away}|${g.home}`.toLowerCase(),g]));live.forEach(g=>{const k=`${g.away}|${g.home}`.toLowerCase(),o=m.get(k)||{};m.set(k,{...o,...g,market:{...(o.market||{}),...(g.market||{})},prediction:{...(o.prediction||{}),...(g.prediction||{})},decision:{...(o.decision||{}),...(g.decision||{})},derived:{...(o.derived||{}),...(g.derived||{})}})});return [...m.values()];}
async function init(){
 state.games=window.TE_WEEK2_BOARD.games||[];render();$("statusText").textContent=`Week 2 board • ${state.games.length} games • loading live model overlay...`;
 try{let r=await fetch("/api/v1/live-board/2",{cache:"no-store"});if(!r.ok)r=await fetch("/api/v1/week-board/2",{cache:"no-store"});if(r.ok){const j=await r.json();if(j.games?.length){state.games=merge(state.games,j.games);render();$("statusText").textContent=`Live model board • ${state.games.length} games`;}}}catch(e){$("statusText").textContent=`Week 2 board • ${state.games.length} games • live overlay unavailable`;}
}
document.addEventListener("click",e=>{const a=e.target.closest("[data-action]");if(!a)return;const x=a.dataset.action;if(x==="enter")showPage("app");if(x==="learn")showPage("learn");if(x==="home")showPage("landing");if(x==="scores")openScores();if(x==="close-scores")closeScores();});
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>{document.querySelectorAll("[data-view]").forEach(x=>x.classList.remove("active"));b.classList.add("active");state.view=b.dataset.view;render();});
$("divisionSelect").onchange=e=>{state.division=e.target.value;render();};$("sortSelect").onchange=e=>{state.sort=e.target.value;render();};$("searchInput").oninput=e=>{state.search=e.target.value.toLowerCase();render();};$("scrim").onclick=closeScores;
init();setInterval(init,60000);
