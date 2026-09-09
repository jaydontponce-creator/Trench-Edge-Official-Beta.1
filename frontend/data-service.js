class TEDataService {
  constructor(){ this.cache = null; this.api = "/api/v1"; }

  normalizeApiGame(x){
    const d = x.decision || {};
    const attr = x.attribution || {};
    const homePts = x.home?.expected_points ?? 0;
    const awayPts = x.away?.expected_points ?? 0;
    const side = d.side || "No qualified market";
    return {
      id: x.game_id,
      away: x.away?.team || "Away",
      home: x.home?.team || "Home",
      time: x.metadata?.kickoff || "Kickoff pending",
      market: x.metadata?.market_label || "Market supplied through API",
      teScore: `${x.away?.team || "Away"} ${awayPts.toFixed(1)} - ${x.home?.team || "Home"} ${homePts.toFixed(1)}`,
      lean: side,
      edge: Number(d.edge || 0),
      status: d.state === "PASS" ? "QUALIFIED" : d.state === "FAIL" ? "NO BET" : "NO BET",
      dqs: x.derived_metrics?.dqs ?? "—",
      ocrs: x.derived_metrics?.ocrs ?? "—",
      dfr: x.derived_metrics?.dfr ?? "—",
      fpse: x.derived_metrics?.fpse ?? "—",
      ecs: Number(attr.ecs || 0),
      dac: attr.dac ?? 0,
      summary: (d.reasons || []).join(" ") || "Calculated by TE V4.1 backend.",
      prediction:{ winProbability: 0.5 },
      marketData:{ current:x.metadata?.market_label || "API market snapshot", open:"Feed pending", movement:"Feed adapter pending" },
      trench:{ offensiveLine:{away:"Calculated input feed",home:"Calculated input feed"}, defensiveLine:{away:"Calculated input feed",home:"Calculated input feed"}, summary:"V4.1 feature inputs are calculated server-side." },
      riskFactors:[
        {label:"Qualification",level:d.state === "PASS" ? "LOW" : "MEDIUM",detail:(d.reasons || []).join(" ")},
        {label:"Live feed readiness",level:"MEDIUM",detail:"Market/injury/weather adapters are separate backend modules and can be connected without changing the UI."}
      ],
      attribution:{
        drivers:(attr.top_drivers || []).map(v=>({name:v.feature,contribution:(v.margin_contribution>=0?"+":"")+Number(v.margin_contribution).toFixed(3)})),
        counterweights:(attr.counterweights || []).map(v=>({name:v.feature,contribution:(v.margin_contribution>=0?"+":"")+Number(v.margin_contribution).toFixed(3)})),
        ecs:Number(attr.ecs || 0), dac:attr.dac || 0, method:attr.method || "TE Attribution & Explainability Layer v1",
        note:"Generated from the V4.1 backend contribution vector."
      },
      dataQuality:{snapshot:x.metadata?.snapshot || "API calculation",marketFeed:"backend",injuryFeed:"adapter pending",weatherFeed:"adapter pending",modelVersion:x.model_version || "TE V4.1"},
      results:{status:"Pregame",finalScore:null,atsResult:null,profitLoss:null}
    };
  }

  async getGames(){
    if(this.cache) return this.cache;
    try{
      const r = await fetch(`${this.api}/games`,{cache:"no-store"});
      if(!r.ok) throw new Error("API unavailable");
      const rows = await r.json();
      if(rows.length){ this.cache = rows.map(x=>this.normalizeApiGame(x)); return this.cache; }
    }catch(e){}
    // UI remains usable until Week 2 standardized inputs are loaded into the backend.
    this.cache = window.TE_GAMES_FALLBACK || [];
    return this.cache;
  }

  async getGame(id){ const games=await this.getGames(); return games.find(g=>g.id===id); }
  async health(){ const r=await fetch(`${this.api}/health`); return r.json(); }
  async recalculate(){
    const r=await fetch(`${this.api}/recalculate-week2`,{method:"POST"});
    if(!r.ok) throw new Error("Recalculation failed");
    this.cache=null; return r.json();
  }
}
window.teDataService = new TEDataService();
