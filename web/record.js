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
if(typeof module!=='undefined')module.exports={uniquePredictions,resultCategory,predictionCounts};
