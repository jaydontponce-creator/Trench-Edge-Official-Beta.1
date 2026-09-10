const state={games:[],selected:null,view:"all",tab:"overview",division:"all"};
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
    let line=m.total;
    const hit=String(m.display||"").match(/(?:O\/U|Total)\s*([0-9.]+)/i);
    if(line==null&&hit)line=hit[1];
    const side=String(d.side).toLowerCase().includes("under")?"Under":"Over";
    return line!=null?`${side} ${line}`:d.side;
  }
  return d.side;
}
function riskWord(x){if(x==null)return"Pending";x=Number(x);return x>=65?"High":x>=45?"Moderate":"Low";}
function qualityWord(x){if(x==null)return"Pending";x=Number(x);return x>=80?"Strong":x>=65?"Usable":"Limited";}
function colors(g){return {home:g.branding?.home?.primary||"#35d07f",away:g.branding?.away?.primary||"#476582"};}
function winProb(g){
  const m=Number(g.prediction?.model_margin_home);
  if(!Number.isFinite(m))return null;
  const h=1/(1+Math.exp(-0.16*m));return {home:h,away:1-h};
}

const FBS_SCHOOLS=new Set(["Air Force", "Akron", "Alabama", "Appalachian State", "Arizona", "Arizona State", "Arkansas", "Arkansas State", "Army", "Auburn", "Ball State", "Baylor", "Boise State", "Boston College", "Bowling Green", "Buffalo", "BYU", "California", "Central Michigan", "Charlotte", "Cincinnati", "Clemson", "Coastal Carolina", "Colorado", "Colorado State", "Delaware", "Duke", "East Carolina", "Eastern Michigan", "FAU", "FIU", "Florida", "Florida State", "Fresno State", "Georgia", "Georgia Southern", "Georgia State", "Georgia Tech", "Hawaii", "Houston", "Illinois", "Indiana", "Iowa", "Iowa State", "Jacksonville State", "James Madison", "Kansas", "Kansas State", "Kennesaw State", "Kent State", "Kentucky", "Liberty", "Louisiana", "Louisiana Tech", "Louisville", "LSU", "Marshall", "Maryland", "Memphis", "Miami (FL)", "Miami (OH)", "Michigan", "Michigan State", "Middle Tennessee", "Minnesota", "Mississippi State", "Missouri", "Missouri State", "Navy", "NC State", "Nebraska", "Nevada", "New Mexico", "New Mexico State", "North Carolina", "North Texas", "Northern Illinois", "Northwestern", "Notre Dame", "Ohio", "Ohio State", "Oklahoma", "Oklahoma State", "Old Dominion", "Ole Miss", "Oregon", "Oregon State", "Penn State", "Pittsburgh", "Purdue", "Rice", "Rutgers", "Sam Houston", "San Diego State", "San Jose State", "SMU", "South Alabama", "South Carolina", "South Florida", "Southern Miss", "Stanford", "Syracuse", "TCU", "Temple", "Tennessee", "Texas", "Texas A&M", "Texas State", "Texas Tech", "Toledo", "Troy", "Tulane", "Tulsa", "UAB", "UCF", "UCLA", "UConn", "ULM", "UMass", "UNLV", "USC", "Utah", "Utah State", "UTEP", "UTSA", "Vanderbilt", "Virginia", "Virginia Tech", "Wake Forest", "Washington", "Washington State", "West Virginia", "Western Kentucky", "Western Michigan", "Wisconsin", "Wyoming"]);
function teamDivision(team){return FBS_SCHOOLS.has(team)?"FBS":"FCS";}
function matchupDivision(g){
 const a=teamDivision(g.away),h=teamDivision(g.home);
 if(a!==h)return "cross";
 return a.toLowerCase();
}
function missingDataItems(g){
 const items=[];
 const prov=g.feature_provenance||{};
 const scan=(side,obj)=>Object.entries(obj||{}).forEach(([k,v])=>{
   if(String(v).includes("imputation"))items.push(`${side} ${friendlyField(k)}`);
   if(String(v).includes("pending_weather"))items.push("Weather");
 });
 scan(g.away,prov.away); scan(g.home,prov.home);
 if(g.market?.home_spread==null && g.market?.total==null)items.push("Live market line");
 if(g.live_meta && g.live_meta.injury_feed_ready===false)items.push("Verified injury availability");
 if((g.derived||{}).dqs==null)items.push("Data-quality inputs");
 return [...new Set(items)].slice(0,8);
}
function friendlyField(k){
 const map={
  defensive_weakness:"defensive form",off_epa:"offensive EPA",defensive_turnover_generation:"turnover defense",
  pass_epa:"passing EPA",opp_special_teams:"opponent special teams",run_mote:"run trench grade",
  pace:"pace",special_teams:"special teams",first_down_rate:"first-down rate",pass_mote:"pass trench grade",
  explosiveness:"explosiveness",rush_epa:"rushing EPA",opp_turnover_generation:"opponent turnover generation"
 };
 return map[k]||String(k).replaceAll("_"," ");
}
function waitingBar(g){
 const missing=missingDataItems(g);
 if(!missing.length)return `<div class=waiting-bar><strong>Data status: complete enough to evaluate</strong><span class=small>TE is not currently waiting on a flagged core input for this matchup.</span></div>`;
 return `<div class=waiting-bar><strong>TE is still waiting on ${missing.length} input${missing.length===1?"":"s"}</strong>
 <span class=small>The current projection remains live and provisional. These inputs could materially change the score, probability, or recommended wager.</span>
 <div class=waiting-items>${missing.map(x=>`<span class=waiting-pill>${x}</span>`).join("")}</div></div>`;
}

function filtered(){
  let a=[...state.games],q=$("search").value.toLowerCase().trim();
  if(q)a=a.filter(g=>(g.away+" "+g.home).toLowerCase().includes(q)); if(state.division!=="all")a=a.filter(g=>matchupDivision(g)===state.division);
  if(state.view==="qualified")a=a.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state));
  if(state.view==="value")a=a.filter(g=>Math.abs(Number(g.decision?.edge||0))>=2.5);
  if(state.view==="fbs")a=a.filter(g=>String(g.classification||"").includes("FBS"));
  if(state.view==="fcs")a=a.filter(g=>g.classification==="FCS");
  const s=$("sort").value;
 if(s==="dqs") a.sort((x,y)=>(y.derived?.dqs??-999)-(x.derived?.dqs??-999));
 else if(s==="ocrs") a.sort((x,y)=>(x.derived?.ocrs??999)-(y.derived?.ocrs??999));
 else if(s==="edge") a.sort((x,y)=>Math.abs(y.decision?.edge||0)-Math.abs(x.decision?.edge||0));
 return a;
}
function render(){
  const a=filtered();
  if(a.length&&!a.some(g=>g.id===state.selected))state.selected=a[0].id;
  const q=state.games.filter(g=>["PASS","QUALIFIED"].includes(g.decision?.state)).length;
  $("summary").innerHTML=`<div class=chip><b>${state.games.length}</b><span>Games</span></div><div class=chip><b>${q}</b><span>Qualified</span></div><div class=chip><b>${state.games.length-q}</b><span>Pass / wait</span></div>`;
  $("games").innerHTML=a.length?a.map(g=>`<div class="game ${g.id===state.selected?"active":""}" data-id="${g.id}"><div class=row><div><div class=match>${g.away} @ ${g.home}</div><div class=small>${market(g)}</div></div><span class="badge ${g.decision?.state||"NEEDS_DATA"}">${verdict(g)}</span></div><div class="row small" style="margin-top:8px"><span>${g.prediction?.away_points==null?"Analysis pending":`Projected ${g.away} ${whole(g.prediction.away_points)}, ${g.home} ${whole(g.prediction.home_points)}`}</span><span>${g.decision?.edge==null?"":`${one(Math.abs(g.decision.edge))} pt value`}</span></div></div>`).join(""):`<div class=panel>No games match this filter.</div>`;
  document.querySelectorAll(".game").forEach(el=>el.onclick=()=>{state.selected=el.dataset.id;state.tab="overview";render();});
  renderDetail();
}
function tab(id,label){return `<button class="tab ${state.tab===id?"active":""}" data-tab="${id}">${label}</button>`}
function renderDetail(){
  const g=state.games.find(x=>x.id===state.selected)||filtered()[0];
  if(!g){$("detail").innerHTML="<div class=panel>Select a game.</div>";return;}
  const p=g.prediction||{},d=g.derived||{},ev=g.ev||{},wp=winProb(g),c=colors(g);
  $("detail").innerHTML=`<div class=hero><div class=row><div><div class=eyebrow>TE GAME ANALYSIS</div><h2>${g.away} @ ${g.home}</h2><div class=small>${market(g)}</div></div><span class="badge ${g.decision?.state||"NEEDS_DATA"}">${verdict(g)}</span></div><div class=score>${p.away_points==null?"Projection pending":`${g.away} ${whole(p.away_points)} • ${g.home} ${whole(p.home_points)}`}</div><div class=metrics><div class=metric><span>Bet win chance</span><b>${pct(ev.probability)}</b></div><div class=metric><span>Betting value</span><b>${g.decision?.edge==null?"—":one(Math.abs(g.decision.edge))+" pts"}</b></div><div class=metric><span>Data quality</span><b>${qualityWord(d.dqs)}</b></div><div class=metric><span>Game risk</span><b>${riskWord(d.ocrs)}</b></div></div><div class=tabs>${tab("overview","Overview")}${tab("why","Why TE Likes It")}${tab("risk","Risk Factors")}${tab("advanced","Advanced")}</div><div class=panel>${panel(g,wp,c)}</div></div>`;
  document.querySelectorAll(".tab").forEach(el=>el.onclick=()=>{state.tab=el.dataset.tab;renderDetail();});
}
function panel(g,wp,c){
  const p=g.prediction||{},d=g.derived||{},a=g.attribution||{},ev=g.ev||{};
  if(state.tab==="overview"){
    let chart="";
    if(wp){const hp=Math.round(wp.home*100),ap=100-hp;chart=`<div class=win><div class=donut style="background:conic-gradient(${c.home} ${hp}%,${c.away} 0)"><b>${hp}%</b></div><div class=key><div class=keyrow><span><i class=swatch style="background:${c.home}"></i>${g.home}</span><b>${hp}%</b></div><div class=keyrow><span><i class=swatch style="background:${c.away}"></i>${g.away}</span><b>${ap}%</b></div><div class=explain>Outright win probability is separate from the probability that the preferred wager wins.</div></div></div>`;}
    return `<div class=item><span>Projected score</span><b>${p.away_points==null?"Pending":`${g.away} ${whole(p.away_points)} • ${g.home} ${whole(p.home_points)}`}</b></div><div class=item><span>Current betting line</span><b>${market(g)}</b></div><div class=item><span>TE preferred wager</span><b>${preferred(g)}</b></div>${chart}`;
  }
  if(state.tab==="why"){
    const dr=(a.drivers||[]).slice(0,3);
    return dr.length?dr.map((x,i)=>`<div class=item><span>${i+1}. ${x.name}</span><b>Supports pick</b></div>`).join(""):`<div class=explain>Driver analysis will populate when the live model has enough data.</div>`;
  }
  if(state.tab==="risk"){
    return `<div class=explain>Risk measures how vulnerable a prediction is to realistic events that can push the game away from the model's central expectation. Pressure, sacks, turnovers, stalled drives, short fields, injuries, special-teams swings, weather, or an unusual game script can all matter.</div><div class=item><span>Overall game risk</span><b>${riskWord(d.ocrs)}</b></div><div class=item><span>Drive-stalling risk</span><b>${riskWord(d.dfr)}</b></div><div class=item><span>Field-position / special-teams risk</span><b>${riskWord(d.fpse)}</b></div>`;
  }
  return `<div class=explain>Advanced diagnostics are optional and expose the model's internal calculations.</div><div class=item><span>Run trench matchup</span><b>${one(g.trench?.away?.RunMOTE)} / ${one(g.trench?.home?.RunMOTE)}</b></div><div class=item><span>Pass trench matchup</span><b>${one(g.trench?.away?.PassMOTE)} / ${one(g.trench?.home?.PassMOTE)}</b></div><div class=item><span>Data Quality Score</span><b>${one(d.dqs)}</b></div><div class=item><span>Context Risk Score</span><b>${one(d.ocrs)}</b></div>`;
}


const scoreboard={games:[],lastServerUpdate:0};
function formatKickoffCST(v){
 if(!v)return "Kickoff TBA";
 const d=new Date(v);
 if(Number.isNaN(d.getTime()))return String(v);
 return new Intl.DateTimeFormat("en-US",{timeZone:"America/Chicago",weekday:"short",hour:"numeric",minute:"2-digit"}).format(d)+" CST";
}
function scoreStatus(g){
 if(g.completed)return "FINAL";
 const raw=String(g.status||"").toLowerCase();
 if(raw.includes("in_progress")||raw.includes("live")||g.live)return "LIVE";
 return "SCHEDULED";
}

const HELMET_CONFIG={
 "Alabama":{shell:"#9E1B32",text:"#FFFFFF",mark:"A",stripe:"#FFFFFF",facemask:"#FFFFFF"},
 "Kentucky":{shell:"#0033A0",text:"#FFFFFF",mark:"UK",stripe:"#FFFFFF",facemask:"#FFFFFF"},
 "Oklahoma":{shell:"#841617",text:"#FFFFFF",mark:"OU",stripe:"#FFFFFF",facemask:"#FFFFFF"},
 "Michigan":{shell:"#FFCB05",text:"#00274C",mark:"M",stripe:"#00274C",facemask:"#00274C"},
 "Iowa State":{shell:"#C8102E",text:"#F1BE48",mark:"I",stripe:"#F1BE48",facemask:"#F1BE48"},
 "Iowa":{shell:"#000000",text:"#FFCD00",mark:"I",stripe:"#FFCD00",facemask:"#FFCD00"},
 "Ohio State":{shell:"#B0B7BC",text:"#BB0000",mark:"O",stripe:"#BB0000",facemask:"#BB0000"},
 "Texas":{shell:"#FFFFFF",text:"#BF5700",mark:"UT",stripe:"#BF5700",facemask:"#FFFFFF"},
 "Texas A&M":{shell:"#500000",text:"#FFFFFF",mark:"ATM",stripe:"#FFFFFF",facemask:"#FFFFFF"},
 "Georgia":{shell:"#BA0C2F",text:"#FFFFFF",mark:"G",stripe:"#000000",facemask:"#000000"},
 "LSU":{shell:"#FDD023",text:"#461D7C",mark:"LSU",stripe:"#461D7C",facemask:"#461D7C"},
 "Notre Dame":{shell:"#C99700",text:"#0C2340",mark:"ND",stripe:"transparent",facemask:"#0C2340"},
 "USC":{shell:"#990000",text:"#FFC72C",mark:"SC",stripe:"#FFC72C",facemask:"#FFC72C"},
 "Oregon":{shell:"#154733",text:"#FEE123",mark:"O",stripe:"#FEE123",facemask:"#FEE123"},
 "Tennessee":{shell:"#FFFFFF",text:"#FF8200",mark:"T",stripe:"#FF8200",facemask:"#FF8200"},
 "Penn State":{shell:"#FFFFFF",text:"#041E42",mark:"PSU",stripe:"#041E42",facemask:"#041E42"},
 "Florida":{shell:"#0021A5",text:"#FA4616",mark:"F",stripe:"#FA4616",facemask:"#FA4616"},
 "Miami (FL)":{shell:"#FFFFFF",text:"#005030",mark:"U",stripe:"#F47321",facemask:"#FFFFFF"},
 "Clemson":{shell:"#F56600",text:"#FFFFFF",mark:"C",stripe:"#522D80",facemask:"#FFFFFF"},
 "Auburn":{shell:"#0C2340",text:"#F26522",mark:"AU",stripe:"#F26522",facemask:"#FFFFFF"},
 "Texas Tech":{shell:"#000000",text:"#CC0000",mark:"TT",stripe:"#CC0000",facemask:"#CC0000"},
 "Ole Miss":{shell:"#14213D",text:"#CE1126",mark:"OM",stripe:"#CE1126",facemask:"#CE1126"},
 "BYU":{shell:"#FFFFFF",text:"#002E5D",mark:"Y",stripe:"#002E5D",facemask:"#002E5D"},
 "Washington":{shell:"#4B2E83",text:"#B7A57A",mark:"W",stripe:"#B7A57A",facemask:"#B7A57A"},
 "Michigan State":{shell:"#18453B",text:"#FFFFFF",mark:"S",stripe:"#FFFFFF",facemask:"#FFFFFF"},
 "Wisconsin":{shell:"#FFFFFF",text:"#C5050C",mark:"W",stripe:"#C5050C",facemask:"#C5050C"},
 "Nebraska":{shell:"#FFFFFF",text:"#E41C38",mark:"N",stripe:"#E41C38",facemask:"#E41C38"},
 "Colorado":{shell:"#000000",text:"#CFB87C",mark:"CU",stripe:"#CFB87C",facemask:"#CFB87C"},
 "UCLA":{shell:"#2D68C4",text:"#F2A900",mark:"UCLA",stripe:"#F2A900",facemask:"#F2A900"}
};
function helmetConfig(team,g,side){
 const b=g.branding?.[side]||{};
 const cfg=HELMET_CONFIG[team]||{};
 return {
   shell:cfg.shell||b.primary||colors(g)[side],
   text:cfg.text||b.secondary||"#FFFFFF",
   mark:cfg.mark||shortMark(team),
   stripe:cfg.stripe||b.secondary||"transparent",
   facemask:cfg.facemask||b.secondary||"#D5D5D5",
   logo:b.logo||b.logo_url||b.logoUrl||null
 };
}
function shortMark(team){
 const parts=String(team||"").replace(/[()]/g,"").split(/\s+/).filter(Boolean);
 if(parts.length===1)return parts[0].slice(0,3).toUpperCase();
 return parts.slice(0,2).map(x=>x[0]).join("").toUpperCase();
}
function helmetHTML(team,g,side){
 const h=helmetConfig(team,g,side);
 const inside=h.logo?`<img class=helmet-logo src="${h.logo}" alt="">`:`<span class=helmet-monogram>${h.mark}</span>`;
 return `<div class=helmet-real style="background:${h.shell};--helmet-text:${h.text};--stripe:${h.stripe};--facemask:${h.facemask}">
   <span class=helmet-stripe></span>${inside}
 </div>`;
}
function venueDescription(g){
 const venue=g.venue||"venue to be announced";
 const city=g.venue_city||g.city||g.location?.city||null;
 const state=g.venue_state||g.state||g.location?.state||null;
 const place=[city,state].filter(Boolean).join(", ");
 if(venue==="venue to be announced")return "Venue information has not been published yet.";
 return place?`This matchup is scheduled at ${venue} in ${place}.`:`This matchup is scheduled at ${venue}.`;
}

function scoreboardCard(g){
 const status=scoreStatus(g),live=status==="LIVE";
 return `<div class=score-game>
  <div class=score-meta>
    <span class=kickoff>${formatKickoffCST(g.kickoff)}</span>
    <span class=venue-short>${g.venue||"Venue TBA"}</span>
  </div>
  <div class=helmet-matchup>
    <div class=helmet-side>
      ${helmetHTML(g.away,g,"away")}
      <div class=score-team-name>${g.away}</div>
      <div class=score-number>${g.away_score??"–"}</div>
    </div>
    <div class=vs-badge>VS</div>
    <div class=helmet-side>
      ${helmetHTML(g.home,g,"home")}
      <div class=score-team-name>${g.home}</div>
      <div class=score-number>${g.home_score??"–"}</div>
    </div>
  </div>
  <div class=score-status><span>${live?'<span class=live-dot></span>LIVE':status}</span><span class=game-clock>${g.clock||g.detail||""}</span></div>
  <div class=game-location><strong>Game location:</strong> ${venueDescription(g)}</div>
 </div>`;
}
function renderScoreboard(){
 const list=[...scoreboard.games].sort((a,b)=>new Date(a.kickoff||0)-new Date(b.kickoff||0));
 $("scoreboardList").innerHTML=list.length?list.map(scoreboardCard).join(""):`<div class=panel>No scoreboard data available yet.</div>`;
}
async function fetchScoreboard(){
 try{
  const r=await fetch("/api/v1/scoreboard/2",{cache:"no-store"});
  if(!r.ok)throw new Error("scoreboard unavailable");
  const j=await r.json();
  scoreboard.games=(j.games&&j.games.length)?j.games:state.games.map(g=>({...g,away_score:null,home_score:null,status:"scheduled",detail:"Scheduled"}));
  scoreboard.lastServerUpdate=j.refreshed_epoch||0;
  $("scoreboardUpdated").textContent=`Feed checked ${new Date((j.refreshed_epoch||Date.now()/1000)*1000).toLocaleTimeString()} • source updates when provider publishes`;
  renderScoreboard();
 }catch(e){
  scoreboard.games=state.games.map(g=>({...g,away_score:null,home_score:null,status:"scheduled",detail:"Scheduled"})); $("scoreboardUpdated").textContent="Schedule loaded • live score feed temporarily unavailable"; renderScoreboard();
 }
}
function openScoreboard(){ $("scoreboardDrawer").classList.add("open"); $("scoreboardScrim").classList.add("open"); $("scoreboardDrawer").setAttribute("aria-hidden","false"); fetchScoreboard(); }
function closeScoreboard(){ $("scoreboardDrawer").classList.remove("open"); $("scoreboardScrim").classList.remove("open"); $("scoreboardDrawer").setAttribute("aria-hidden","true"); }
$("scoreboardBtn").onclick=openScoreboard;
$("scoreboardClose").onclick=closeScoreboard;
$("scoreboardScrim").onclick=closeScoreboard;
$("divisionToggle").value="all"; $("divisionToggle").onchange=e=>{state.division=e.target.value||"all";render();};
setInterval(()=>{ if($("scoreboardDrawer").classList.contains("open")) fetchScoreboard(); },5000);

function gameKey(g){return `${String(g.away||"").toLowerCase()}|${String(g.home||"").toLowerCase()}`;}
function mergeBoards(base,live){
 const map=new Map((base||[]).map(g=>[gameKey(g),g]));
 (live||[]).forEach(g=>{
   const k=gameKey(g),old=map.get(k)||{};
   map.set(k,{...old,...g,
     market:{...(old.market||{}),...(g.market||{})},
     prediction:{...(old.prediction||{}),...(g.prediction||{})},
     decision:{...(old.decision||{}),...(g.decision||{})},
     derived:{...(old.derived||{}),...(g.derived||{})},
     branding:{...(old.branding||{}),...(g.branding||{})}
   });
 });
 return [...map.values()];
}
async function fetchBoard(){
 let base=[];
 try{
   const local=await fetch("week2_board.json",{cache:"no-store"});
   const localJson=await local.json();
   base=Array.isArray(localJson.games)?localJson.games:[];
 }catch(e){}
 if(base.length){
   state.games=base;
   $("statusText").textContent=`Week 2 board • ${base.length} games • loading live model overlay...`;
   render();
 }
 try{
   let r=await fetch("/api/v1/live-board/2",{cache:"no-store"});
   if(!r.ok)r=await fetch("/api/v1/week-board/2",{cache:"no-store"});
   if(!r.ok)throw new Error("API unavailable");
   const j=await r.json();
   const live=Array.isArray(j.games)?j.games:[];
   state.games=mergeBoards(base,live);
   $("statusText").textContent=`Live model board • ${state.games.length} games • updated ${new Date((j.refreshed_epoch||Date.now()/1000)*1000).toLocaleTimeString()}`;
   render();
 }catch(e){
   if(base.length){
     state.games=base;
     $("statusText").textContent=`Week 2 board • ${base.length} games • live overlay temporarily unavailable`;
     render();
   }else{
     $("statusText").textContent="Unable to load matchup data";
   }
 }
}
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>{
 if(b.dataset.view==="scores"){ openScoreboard(); return; }
 document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));
 b.classList.add("active");
 state.view=b.dataset.view;
 render();
});
$("search").oninput=render;$("sort").onchange=render;
load();
