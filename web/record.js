'use strict';
function uniquePredictions(picks,policy){
 const groups=new Map();
 for(const p of picks){const prior=groups.get(p.id);const better=!prior?1:Number(p.result_status!=='not_pregame')-Number(prior.result_status!=='not_pregame')||Number(p.prediction_policy===policy)-Number(prior.prediction_policy===policy)||Date.parse(prior.generated_at)-Date.parse(p.generated_at);if(better>0)groups.set(p.id,p);}
 return [...groups.values()].sort((a,b)=>String(b.event_start_utc||b.date).localeCompare(String(a.event_start_utc||a.date)));
}
function resultCategory(p,now=Date.now()){
 if(p.result_status==='not_pregame'||p.result_status==='unscored'||p.result_status==='canceled'||p.result_status==='postponed')return 'unscored';
 if(typeof p.correct==='boolean')return p.correct?'correct':'incorrect';
 if(p.outcome)return 'unscored';
 const start=Date.parse(p.event_start_utc);
 if(Number.isFinite(start)&&start>now)return 'scheduled';
 if(p.result_status==='in_progress')return 'pending';
 if(p.result_status==='awaiting_result'||!Number.isFinite(start)||now-start>12*3600000)return 'awaiting';
 return 'pending';
}
function predictionCounts(picks,now=Date.now()){
 const counts={correct:0,incorrect:0,pending:0,awaiting:0,unscored:0,scheduled:0};
 for(const p of picks)counts[resultCategory(p,now)]++;
 counts.graded=counts.correct+counts.incorrect;counts.accuracy=counts.graded?counts.correct/counts.graded:null;return counts;
}
const SCOREBOARD_ALIASES={"NFL":{"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers","HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers","LAR":"Los Angeles Rams","MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SF":"San Francisco 49ers","SEA":"Seattle Seahawks","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"},"NHL":{"SEA":"Seattle Kraken","CGY":"Calgary Flames","LAK":"Los Angeles Kings","SJS":"San Jose Sharks","ANA":"Anaheim Ducks","BOS":"Boston Bruins","BUF":"Buffalo Sabres","CAR":"Carolina Hurricanes","CHI":"Chicago Blackhawks","COL":"Colorado Avalanche","CBJ":"Columbus Blue Jackets","DAL":"Dallas Stars","DET":"Detroit Red Wings","EDM":"Edmonton Oilers","FLA":"Florida Panthers","MIN":"Minnesota Wild","MTL":"Montreal Canadiens","NSH":"Nashville Predators","NJD":"New Jersey Devils","NYI":"New York Islanders","NYR":"New York Rangers","OTT":"Ottawa Senators","PHI":"Philadelphia Flyers","PIT":"Pittsburgh Penguins","STL":"St. Louis Blues","TBL":"Tampa Bay Lightning","TOR":"Toronto Maple Leafs","UTA":"Utah Mammoth","VAN":"Vancouver Canucks","VGK":"Vegas Golden Knights","WSH":"Washington Capitals","WPG":"Winnipeg Jets"}};
function scoreboardTeam(name,league){if(league==='NFL')name=({LA:'LAR',JAC:'JAX'})[name]||name;name=SCOREBOARD_ALIASES[league]?.[name]||name;return String(name||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace('la clippers','los angeles clippers').replace(/[^a-z0-9]/g,'');}
function scoreboardIdentity(id){return String(id||'').replace(/^(espn-(nba|nfl|nhl|cfb|wnba|ufc)-|nflverse-|mlb-|nhl-|nba-cdn-)/,'');}
function scoreboardPick(game,picks,league){
 const same=p=>scoreboardTeam(p.home,league)===scoreboardTeam(game.home,league)&&scoreboardTeam(p.away,league)===scoreboardTeam(game.away,league);
 const valid=p=>p.result_status!=='not_pregame'&&Number.isFinite(Date.parse(p.generated_at))&&(!game.start_time||Date.parse(p.generated_at)<Date.parse(game.start_time));
 const candidates=picks.filter(p=>same(p)&&valid(p));let matches=candidates.filter(p=>scoreboardIdentity(p.id)===scoreboardIdentity(game.id));
 if(!matches.length)matches=candidates.filter(p=>Number.isFinite(Date.parse(p.event_start_utc))&&Number.isFinite(Date.parse(game.start_time))&&Math.abs(Date.parse(p.event_start_utc)-Date.parse(game.start_time))<15*60000);
 if(!matches.length&&league!=='MLB'){const legacy=candidates.filter(p=>!p.event_start_utc&&p.date===game.date);if(new Set(legacy.map(p=>scoreboardIdentity(p.id))).size===1)matches=legacy;}
 return matches.sort((a,b)=>Date.parse(a.generated_at)-Date.parse(b.generated_at))[0]||null;
}
if(typeof module!=='undefined')module.exports={uniquePredictions,resultCategory,predictionCounts,scoreboardPick,scoreboardTeam};
