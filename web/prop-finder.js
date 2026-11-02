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
function findPlayerProps(players,fixture,{minimum=.7,minGames=10,side='over',market='all',now=Date.now(),maxAgeDays=30}={}){
 if(!fixture||!Number.isFinite(Date.parse(fixture.start_time))||Date.parse(fixture.start_time)<=now)return [];
 const start=Date.parse(fixture.start_time),candidates=[];
 for(const player of players){
  if(![fixture.home,fixture.away].includes(player.team))continue;
  const games=player.games.filter(g=>Date.parse(g.start_time)<Math.min(start,now)).sort((a,b)=>Date.parse(b.start_time)-Date.parse(a.start_time));
  if(!games.length||now-Date.parse(games[0].start_time)>maxAgeDays*86400000)continue;
  for(const [stat,lines] of Object.entries(PROP_LINES)){
   if(market!=='all'&&market!==stat)continue;
   const observations=games.filter(g=>Number.isFinite(g.values[stat])).slice(0,20);
   if(observations.length<minGames)continue;
   let best=null;
   for(const direction of side==='both'?['over','under']:[side]){
    // Strongest threshold that still meets the user's minimum, rather than many redundant lines.
    const ordered=direction==='over'?[...lines].reverse():lines;
    for(const line of ordered){
     const hit=g=>direction==='over'?g.values[stat]>line:g.values[stat]<line;
     const hits=observations.filter(hit).length,n=observations.length,score=(hits+2)/(n+4);
     if(score<minimum)continue;
     const recent=observations.slice(0,5),recentRate=recent.filter(hit).length/recent.length;
     if(recentRate<minimum)continue;
     const z=1.96,p=hits/n,den=1+z*z/n,lower=(p+z*z/(2*n)-z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den;
     let streak=0;for(const g of observations){if(!hit(g))break;streak++;}
     const candidate={player:player.name,player_id:player.id,team:player.team,market:stat,line,side:direction,score,hits,n,lower,streak,recentHits:recent.filter(hit).length,recentN:recent.length,observations,latest:observations[0].start_time,event_id:fixture.id};
     if(!best||candidate.score>best.score)best=candidate;
     break;
    }
   }
   if(best)candidates.push(best);
  }
 }
 return candidates.sort((a,b)=>b.lower-a.lower||b.score-a.score||b.n-a.n||a.player.localeCompare(b.player)||a.market.localeCompare(b.market));
}
if(typeof module!=='undefined')module.exports={findPlayerProps,PROP_LINES};
