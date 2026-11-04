'use strict';
// Fixed research thresholds, independent of the observed outcomes. Not sportsbook quotes.
const PROP_LINES={
 'Points':[9.5,14.5,19.5,24.5,29.5,34.5], 'Rebounds':[3.5,5.5,7.5,9.5,11.5], 'Assists':[2.5,4.5,6.5,8.5],
 'Threes made':[.5,1.5,2.5,3.5], 'Steals':[.5,1.5], 'Blocks':[.5,1.5], 'Points + rebounds + assists':[19.5,24.5,29.5,34.5,39.5,44.5],
 'Passing yards':[149.5,174.5,199.5,224.5,249.5,274.5], 'Passing TDs':[.5,1.5,2.5], 'Rushing yards':[24.5,39.5,49.5,59.5,74.5,99.5],
 'Receiving yards':[24.5,39.5,49.5,59.5,74.5,99.5], 'Receptions':[2.5,3.5,4.5,5.5,6.5],
 'Hits':[.5,1.5], 'Home runs':[.5], 'Runs':[.5,1.5], 'RBIs':[.5,1.5], 'Pitcher strikeouts':[2.5,3.5,4.5,5.5,6.5,7.5],
 'Shots on goal':[1.5,2.5,3.5,4.5], 'Goals':[.5,1.5], 'Saves':[19.5,24.5,29.5,34.5]
};

function playerAvailability(player,report,now=Date.now()){
 const checked=Date.parse(report?.checked),valid=Date.parse(report?.valid_until);
 if(report?.status!=='ok'||!Number.isFinite(checked)||checked>now||!Number.isFinite(valid)||now>=valid)return {eligible:false,status:'Injury coverage unverified',category:'unverified'};
 const listed=Object.values(report.teams||{}).flat().filter(p=>String(p.player_id)===String(player.id));
 const match=listed.find(p=>p.team===player.team);
 if(!match&&listed.length)return {eligible:false,status:'Reported team differs from last observed team',category:'roster_review'};
 if(!match)return {eligible:true,status:'Not listed · active role unverified',category:'not_listed'};
 return {eligible:match.category==='listed_active',status:match.status,category:match.category,reported_at:match.reported_at};
}

function findPlayerProps(players,fixture,{minimum=.7,minGames=10,side='over',market='all',now=Date.now(),maxAgeDays=30,maxForecastDays=14,injuryReport=null,requireInjuryReport=false,historicalOnly=false,allTeams=false,perfectOnly=false,lookback=20}={}){
 if(!historicalOnly&&(!fixture||!Number.isFinite(Date.parse(fixture.start_time))||Date.parse(fixture.start_time)<=now||Date.parse(fixture.start_time)-now>maxForecastDays*86400000))return [];
 const start=historicalOnly?now:Date.parse(fixture.start_time),candidates=[];
 for(const player of players){
  if(!allTeams&&![fixture.home,fixture.away].includes(player.team))continue;
  const availability=playerAvailability(player,injuryReport,now);
  if(requireInjuryReport&&!availability.eligible)continue;
  const games=player.games.filter(g=>Date.parse(g.start_time)<Math.min(start,now)).sort((a,b)=>Date.parse(b.start_time)-Date.parse(a.start_time));
  if(!games.length||now-Date.parse(games[0].start_time)>maxAgeDays*86400000)continue;
  for(const [stat,lines] of Object.entries(PROP_LINES)){
   if(market!=='all'&&market!==stat)continue;
   const observations=games.filter(g=>Number.isFinite(g.values[stat])).slice(0,lookback);
   if(observations.length<minGames)continue;
   let best=null;
   for(const direction of side==='both'?['over','under']:[side]){
    // Strongest threshold that still meets the user's minimum, rather than many redundant lines.
    const ordered=direction==='over'?[...lines].reverse():lines;
    for(const line of ordered){
     const hit=g=>direction==='over'?g.values[stat]>line:g.values[stat]<line;
     const hits=observations.filter(hit).length,n=observations.length,score=(hits+2)/(n+4);
     if(perfectOnly?hits!==n:score<minimum)continue;
     const recent=observations.slice(0,5),recentRate=recent.filter(hit).length/recent.length;
     if(recentRate<minimum)continue;
     const z=1.96,p=hits/n,den=1+z*z/n,lower=(p+z*z/(2*n)-z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den;
     let streak=0;for(const g of observations){if(!hit(g))break;streak++;}
     const candidate={player:player.name,player_id:player.id,team:player.team,market:stat,line,side:direction,score,hits,n,lower,streak,recentHits:recent.filter(hit).length,recentN:recent.length,observations,latest:observations[0].start_time,event_id:fixture?.id||null,availability};
     if(!best||candidate.score>best.score)best=candidate;
     break;
    }
   }
   if(best)candidates.push(best);
  }
 }
 return candidates.sort((a,b)=>b.lower-a.lower||b.score-a.score||b.n-a.n||a.player.localeCompare(b.player)||a.market.localeCompare(b.market));
}
function findPerfectProps(players,{sample=10,side='both',market='all',now=Date.now(),injuryReport=null}={}){
 if(![5,10,20].includes(sample))return [];
 return findPlayerProps(players,null,{minimum:0,minGames:sample,lookback:sample,side,market,now,injuryReport,historicalOnly:true,allTeams:true,perfectOnly:true});
}
function findDailyProps(sources,options={}){
 const found=[],seen=new Set();
 for(const source of sources){
  for(const fixture of source.fixtures||[]){
   for(const p of findPlayerProps(source.players||[],fixture,{...options,injuryReport:source.injuryReport,requireInjuryReport:true})){
    const key=JSON.stringify([source.sport,fixture.id,p.player_id,p.market,p.side,p.line]);if(seen.has(key))continue;seen.add(key);
    found.push({...p,sport:source.sport,matchup:fixture.away+' at '+fixture.home,start_time:fixture.start_time,checked:source.checked});
   }
  }
 }
 return found.sort((a,b)=>b.lower-a.lower||b.score-a.score||b.n-a.n||a.player.localeCompare(b.player)||a.market.localeCompare(b.market)||a.sport.localeCompare(b.sport)||String(a.event_id).localeCompare(String(b.event_id)));
}
if(typeof module!=='undefined')module.exports={findPlayerProps,findPerfectProps,findDailyProps,PROP_LINES,playerAvailability};
