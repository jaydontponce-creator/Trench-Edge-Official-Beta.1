const state={games:[],selected:null,view:"all",tab:"overview"};
const $=id=>document.getElementById(id);
const whole=x=>x==null?"—":Math.round(Number(x));
const one=x=>x==null?"—":Number(x).toFixed(1);
const pct=x=>x==null?"—":Math.round(Number(x)*100)+"%";

function show(id){["landingView","learnView","appView"].forEach(x=>$(x).style.display=x===id?(id==="landingView"?"flex":"block"):"none");}
$("enterBtn").onclick=()=>show("appView");
$("learnBtn").onclick=()=>show("learnView");
$("backBtn").onclick=()=>show("landingView");
$("homeBtn").onclick=()=>show("landingView");

function verdict(g){
 const s=g.decision?.state;
 if(s==="PASS"||s==="QUALIFIED")return "QUALIFIED BET";
 if(s==="FAIL")return "PASS";
 return "WAIT FOR DATA";
}
function market(g){return g.market?.display||[g.market?.home_spread!=null?`Home ${g.market.home_spread}`:"",g.market?.total!=null?`O/U ${g.market.total}`:""].filter(Boolean).join(" • ")||"Market pending";}
function preferred(g){
 const d=g.decision||{},m=g.market||{},t=String(d.market||"").toLowerCase();
 if(!d.side)return "No qualified wager";
 if(t==="total"){
   let line=m.total; const hit=String(m.display||"").match(/(?:O\/U|Total)\s*([0-9.]+)/i);
   if(line==null&&hit)line=hit[1];
   const side=String(d.side).toLowerCase().includes("under")?"Under":"Over";
   return line!=null?`${side} ${line}`:d.side;
 }
 return d.side;
}
function riskWord(x){if(x==null)return"Pending";x=Number(x);return x>=65?"High":x>=45?"Moderate":"Low";}
function qualityWord(x){if(x==null)return"Pending";x=Number(x);return x>=80?"Strong":x>=65?"Usable":"Limited";}

const SCHOOL_COLORS={"Alabama":["#9E1B32","#FFFFFF"],"Kentucky":["#0033A0","#FFFFFF"],"Oklahoma":["#841617","#FDF9D8"],"Michigan":["#00274C","#FFCB05"],"Iowa State":["#C8102E","#F1BE48"],"Iowa":["#FFCD00","#000000"],"UTSA":["#0C2340","#F15A22"],"Texas State":["#501214","#B9975B"],"Tennessee":["#FF8200","#FFFFFF"],"Georgia Tech":["#B3A369","#003057"],"Ohio State":["#BB0000","#666666"],"Texas":["#BF5700","#FFFFFF"],"Missouri":["#F1B82D","#000000"],"Kansas":["#0051BA","#E8000D"],"Oregon":["#154733","#FEE123"],"Oklahoma State":["#FF7300","#000000"],"Arizona State":["#8C1D40","#FFC627"],"Texas A&M":["#500000","#FFFFFF"],"Penn State":["#041E42","#FFFFFF"],"Temple":["#9D2235","#FFFFFF"],"Georgia":["#BA0C2F","#000000"],"Western Kentucky":["#C60C30","#FFFFFF"],"Notre Dame":["#0C2340","#C99700"],"Rice":["#00205B","#FFFFFF"],"BYU":["#002E5D","#FFFFFF"],"Arizona":["#CC0033","#003366"],"LSU":["#461D7C","#FDD023"],"Louisiana Tech":["#002F8B","#E31B23"],"USC":["#990000","#FFC72C"],"Louisiana":["#CE181E","#FFFFFF"],"Utah":["#CC0000","#000000"],"Arkansas":["#9D2235","#FFFFFF"],"Clemson":["#F56600","#522D80"],"Auburn":["#0C2340","#F26522"],"Florida":["#0021A5","#FA4616"],"Louisville":["#AD0000","#000000"],"Miami (FL)":["#F47321","#005030"],"Virginia":["#232D4B","#E57200"],"Indiana":["#990000","#EEEDEB"],"Washington":["#4B2E83","#B7A57A"],"SMU":["#C8102E","#354CA1"],"Houston":["#C8102E","#FFFFFF"],"Ole Miss":["#CE1126","#14213D"],"Texas Tech":["#CC0000","#000000"],"UCF":["#BA9B37","#000000"],"Pittsburgh":["#003594","#FFB81C"],"Boise State":["#0033A0","#D64309"],"Wisconsin":["#C5050C","#FFFFFF"],"Nebraska":["#E41C38","#FFFFFF"],"Colorado":["#CFB87C","#000000"],"Michigan State":["#18453B","#FFFFFF"],"Syracuse":["#F76900","#000E54"],"California":["#003262","#FDB515"],"Boston College":["#8A100B","#B29D6C"],"Rutgers":["#CC0033","#FFFFFF"],"NC State":["#CC0000","#000000"],"Virginia Tech":["#630031","#CF4420"],"West Virginia":["#002855","#EAAA00"],"Minnesota":["#7A0019","#FFCC33"],"Duke":["#003087","#FFFFFF"],"Illinois":["#13294B","#FF5F05"],"Maryland":["#E03A3E","#FFD520"],"Liberty":["#002D62","#C41230"],"Tulane":["#006747","#418FDE"],"South Carolina":["#73000A","#000000"],"Marshall":["#00B140","#FFFFFF"],"Cincinnati":["#E00122","#000000"],"UCLA":["#2D68C4","#F2A900"],"Fresno State":["#DB0032","#13284C"],"Nevada":["#003366","#807F84"],"Hawaii":["#024731","#FFFFFF"],"North Dakota State":["#006633","#FFC72C"]};
function colorPair(team,branding){
 const p=branding?.primary,s=branding?.secondary;
 if(p && p!=="#476582" && p!=="#AFC5D8") return [p,s||"#FFFFFF"];
 return SCHOOL_COLORS[team]||["#E11D2E","#FFFFFF"];
}
function colors(g){
 const h=colorPair(g.home,g.branding?.home),a=colorPair(g.away,g.branding?.away);
 return {home:h[0],away:a[0],homeSecondary:h[1],awaySecondary:a[1]};
}
function winProb(g){
 const m=Number(g.prediction?.model_margin_home);
 if(!Number.isFinite(m))return null;
 const h=1/(1+Math.exp(-0.16*m));return {home:h,away:1-h};
}
function filtered(){
 let a=[...state.games],q=$("search").value.toLowerCase().trim();
 if(q)a=a.filter(g=>(g.away+" "+g.home).toLowerCase().includes(q));
 if(state.view==="qualified")a=a.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state));
 if(state.view==="value")a=a.filter(g=>Math.abs(Number(g.decision?.edge||0))>=2.5);
 if(state.view==="fbs")a=a.filter(g=>String(g.classification||"").includes("FBS"));
 if(state.view==="fcs")a=a.filter(g=>g.classification==="FCS");
 const s=$("sort").value;
 a.sort((x,y)=>s==="dqs"?(y.derived?.dqs||0)-(x.derived?.dqs||0):s==="ocrs"?(x.derived?.ocrs||999)-(y.derived?.ocrs||999):Math.abs(y.decision?.edge||0)-Math.abs(x.decision?.edge||0));
 return a;
}
function tab(id,label){return `<button class="tab ${state.tab===id?"active":""}" data-tab="${id}">${label}</button>`}

function panel(g,wp,c){
 const p=g.prediction||{},d=g.derived||{},a=g.attribution||{},ev=g.ev||{};
 if(state.tab==="overview"){
   let chart="";
   if(wp){
     const hp=Math.round(wp.home*100),ap=100-hp;
     chart=`<div class=win>
       <div class=donut style="background:conic-gradient(${c.home} ${hp}%,${c.away} 0)"><b>${hp}%</b></div>
       <div class=key>
         <div class=keyrow><span><i class=swatch style="background:${c.home}"></i>${g.home}</span><b>${hp}%</b></div>
         <div class=keyrow><span><i class=swatch style="background:${c.away}"></i>${g.away}</span><b>${ap}%</b></div>
         <div class=explain>School colors identify each team. Outright win probability is separate from the probability that the preferred wager wins.</div>
       </div>
     </div>`;
   }
   return `<div class=item><span>Projected score</span><b>${p.away_points==null?"Pending":`${g.away} ${whole(p.away_points)} • ${g.home} ${whole(p.home_points)}`}</b></div>
   <div class=item><span>Current betting line</span><b>${market(g)}</b></div>
   <div class=item><span>TE preferred wager</span><b>${preferred(g)}</b></div>${chart}`;
 }
 if(state.tab==="why"){
   const dr=(a.drivers||[]).slice(0,3);
   return dr.length?dr.map((x,i)=>`<div class=item><span>${i+1}. ${x.name}</span><b>Supports pick</b></div>`).join(""):`<div class=explain>Driver analysis will populate when the live model has enough data.</div>`;
 }
 if(state.tab==="risk"){
   return `<div class=explain>Risk measures how vulnerable a prediction is to realistic events that can push the game away from the model's central expectation. Pressure, sacks, turnovers, stalled drives, short fields, injuries, special-teams swings, weather, or an unusual game script can all matter.</div>
   <div class=item><span>Overall game risk</span><b>${riskWord(d.ocrs)}</b></div>
   <div class=item><span>Drive-stalling risk</span><b>${riskWord(d.dfr)}</b></div>
   <div class=item><span>Field-position / special-teams risk</span><b>${riskWord(d.fpse)}</b></div>`;
 }
 return `<div class=explain>Advanced diagnostics are optional and expose the model's internal calculations.</div>
 <div class=item><span>Run trench matchup</span><b>${one(g.trench?.away?.RunMOTE)} / ${one(g.trench?.home?.RunMOTE)}</b></div>
 <div class=item><span>Pass trench matchup</span><b>${one(g.trench?.away?.PassMOTE)} / ${one(g.trench?.home?.PassMOTE)}</b></div>
 <div class=item><span>Data Quality Score</span><b>${one(d.dqs)}</b></div>
 <div class=item><span>Context Risk Score</span><b>${one(d.ocrs)}</b></div>`;
}

function inlineDetail(g){
 const p=g.prediction||{},d=g.derived||{},ev=g.ev||{},wp=winProb(g),c=colors(g);
 return `<div class="game-detail-inline">
  <div class=score>${p.away_points==null?"Projection pending":`${g.away} ${whole(p.away_points)} • ${g.home} ${whole(p.home_points)}`}</div>
  <div class=metrics>
   <div class=metric><span>Bet win chance</span><b>${pct(ev.probability)}</b></div>
   <div class=metric><span>Betting value</span><b>${g.decision?.edge==null?"—":one(Math.abs(g.decision.edge))+" pts"}</b></div>
   <div class=metric><span>Data quality</span><b>${qualityWord(d.dqs)}</b></div>
   <div class=metric><span>Game risk</span><b>${riskWord(d.ocrs)}</b></div>
  </div>
  <div class=tabs>${tab("overview","Overview")}${tab("why","Why TE Likes It")}${tab("risk","Risk Factors")}${tab("advanced","Advanced")}</div>
  <div class=panel>${panel(g,wp,c)}</div>
 </div>`;
}

function render(){
 const a=filtered();
 if(state.selected&&!a.some(g=>g.id===state.selected))state.selected=null;
 const q=state.games.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state)).length;
 $("summary").innerHTML=`<div class=chip><b>${state.games.length}</b><span>Games</span></div><div class=chip><b>${q}</b><span>Qualified</span></div><div class=chip><b>${state.games.length-q}</b><span>Pass / wait</span></div>`;
 $("games").innerHTML=a.length?a.map(g=>{
   const expanded=g.id===state.selected;
   return `<div class="game ${expanded?"expanded":""}" data-id="${g.id}">
    <div class="game-click-zone" data-id="${g.id}">
     <div class=row><div><div class=match>${g.away} @ ${g.home}</div><div class=small>${market(g)}</div></div><span class="badge ${g.decision?.state||"NEEDS_DATA"}">${verdict(g)}</span></div>
     <div class="row small" style="margin-top:8px"><span>${g.prediction?.away_points==null?"Analysis pending":`Projected ${g.away} ${whole(g.prediction.away_points)}, ${g.home} ${whole(g.prediction.home_points)}`}</span><span>${g.decision?.edge==null?"":`${one(Math.abs(g.decision.edge))} pt value`}</span></div>
     <div class=expand-cue>${expanded?"▲ Hide matchup analysis":"▼ Open matchup analysis"}</div>
    </div>
    ${expanded?inlineDetail(g):""}
   </div>`;
 }).join(""):`<div class=panel>No games match this filter.</div>`;
 document.querySelectorAll(".game-click-zone").forEach(el=>el.onclick=()=>{const id=el.dataset.id;state.selected=state.selected===id?null:id;state.tab="overview";render();});
 document.querySelectorAll(".tab").forEach(el=>el.onclick=(evt)=>{evt.stopPropagation();state.tab=el.dataset.tab;render();});
}

async function fetchBoard(){
 try{
   let r=await fetch("/api/v1/live-board/2",{cache:"no-store"});
   if(!r.ok){r=await fetch("/api/v1/week-board/2",{cache:"no-store"});}
   if(!r.ok)throw new Error("API board unavailable");
   const j=await r.json();
   if(!j.games?.length)throw new Error("API board empty");
   state.games=j.games;
   $("statusText").textContent=j.refreshed_epoch?`Live model board • updated ${new Date(j.refreshed_epoch*1000).toLocaleTimeString()}`:"Live model board";
 }catch(e){
   try{
     const r=await fetch("week2_board.json",{cache:"no-store"});
     const j=await r.json();state.games=j.games||[];
     $("statusText").textContent="Beta fallback board";
   }catch(_){
     $("statusText").textContent="Unable to load matchup data";
   }
 }
 if(state.selected&&!state.games.some(g=>g.id===state.selected))state.selected=null;
 render();
}
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>{document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));b.classList.add("active");state.view=b.dataset.view;render();});
$("search").oninput=render;$("sort").onchange=render;
fetchBoard();setInterval(fetchBoard,60000);
