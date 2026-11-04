"""NBA-specific season maturity and shared-uncertainty research, causal by date."""
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import joblib
import math

VERSION='nba-context-review-v2-schedule-form'

def features(rows,window=20):
 from .nba import feedback_features
 from .model import season
 base,names=feedback_features(rows,window)
 z_index=names.index('uncertainty_adjusted_log_odds');margin_index=names.index('adaptive_margin_strength_difference')
 added=['current_season_games_difference','current_season_maturity','early_season_teams','shared_prediction_error_variance','global_recent_surprise','global_recent_probability_loss','strength_times_shared_uncertainty','margin_times_early_season','home_times_season_maturity','uncertainty_times_global_loss']
 states=defaultdict(lambda:[0,.25]);seasons={};global_error=0.;global_loss=math.log(2);groups=defaultdict(list);extra={}
 for r,x,n in base:groups[r['date']].append((r,x,n))
 for day,group in sorted(groups.items()):
  year=season('NBA',day)
  for team in {r[k] for r,_,_ in group for k in ('home','away')}:
   if seasons.get(team)!=year:states[team]=[0,.25]
   seasons[team]=year
  changes=defaultdict(list);errors=[];losses=[]
  for r,x,n in group:
   h,a=states[r['home']],states[r['away']];maturity=(min(20,h[0])+min(20,a[0]))/40;early=(int(h[0]<10)+int(a[0]<10))/2;uncertainty=h[1]+a[1]
   extra[r['event_id']]=[(min(40,h[0])-min(40,a[0]))/40,maturity,early,uncertainty,global_error,global_loss,x[z_index]*uncertainty,x[margin_index]*early,(1-int(r['neutral']))*maturity,uncertainty*global_loss]
   if r['outcome'] not in ('home','away'):continue
   p=1/(1+math.exp(-max(-20,min(20,x[z_index]))));y=int(r['outcome']=='home');error=y-p;loss=-(y*math.log(p)+(1-y)*math.log1p(-p))
   errors.append(error);losses.append(loss);changes[r['home']].append(error*error);changes[r['away']].append(error*error)
  for team,squares in changes.items():
   count,variance=states[team];rate=1-.9**len(squares);states[team]=[count+len(squares),(1-rate)*variance+rate*sum(squares)/len(squares)]
  if errors:
   rate=1-.98**len(errors);global_error=(1-rate)*global_error+rate*sum(errors)/len(errors);global_loss=(1-rate)*global_loss+rate*sum(losses)/len(losses)
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names+added

def schedule_features(rows,window=20):
 """NBA scoring form and compressed schedules, always frozen before a date."""
 from .nba import feedback_features
 from collections import deque
 rows=sorted(rows,key=lambda r:(r['date'],r['event_id']))
 base,names=feedback_features(rows,window)
 added=['recent_margin_difference','long_margin_difference','margin_trend_difference','venue_margin_difference','back_to_back_difference','three_in_four_difference','four_in_six_difference','fatigue_times_margin']
 games=defaultdict(lambda:deque(maxlen=40));groups=defaultdict(list);extra={}
 for r,x,n in base:groups[r['date']].append((r,x,n))
 for day,group in sorted(groups.items()):
  d=date.fromisoformat(day)
  def summary(team,venue):
   # Do not carry a previous roster's scoring form through the offseason.
   h=[v for v in games[team] if (d-v[0]).days<=120]
   margin=lambda seq:sum(v[1] for v in seq)/(len(seq)+5)
   short=margin(h[-5:]);long=margin(h[-20:]);home=margin([v for v in h if v[2]==venue][-15:])
   gaps=[(d-v[0]).days for v in h]
   return [short,long,short-long,home,float(1 in gaps),float(sum(g<=3 for g in gaps)>=2),float(sum(g<=5 for g in gaps)>=3)]
  for r,x,n in group:
   a=summary(r['home'],'home');b=summary(r['away'],'away');values=[left-right for left,right in zip(a,b)]
   if r['neutral']=='1':values[3]=0.
   values.append(values[4]*values[1]);extra[r['event_id']]=values
  for r,x,n in group:
   if r['outcome'] not in ('home','away'):continue
   margin=max(-30.,min(30.,float(r['home_score'])-float(r['away_score'])))
   games[r['home']].append((d,margin,'home' if r['neutral']=='0' else None));games[r['away']].append((d,-margin,'away' if r['neutral']=='0' else None))
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names+added


def definitions():
 specs=[{'kind':'logistic','variant':'context_nba_context','window':w,'c':c,'decay':False} for w in (10,20,40) for c in (.01,.03,.1,.3)]
 specs += [{'kind':'logistic','variant':'context_nba_context','window':w,'c':.03,'decay':False,'calibrate':'temperature','calibration_refit':True} for w in (10,20,40)]
 specs += [{'kind':'nba_context_blend','variant':'context_nba_context','window':20,'c':.03,'decay':False,'context_weight':w} for w in (.25,.5,.75)]
 for method in ('temperature','sigmoid','decision'):
  for refit in (False,True):specs.append({'kind':'logistic','variant':'context_nba_feedback','window':20,'c':.03,'decay':False,'calibrate':method,'calibration_refit':refit})
 specs += [{'kind':'logistic','variant':'context_nba_schedule','window':w,'c':c,'decay':decay} for w in (10,20) for c in (.01,.03,.1) for decay in (False,True)]
 return specs

def saved_review(root,rows,previous):
 from .nba import RECENT_FROM,CONFIRM_FROM,recent_confirmation
 from .research import review
 from .data import version
 if not previous:return None
 recent=[r for r in rows if r['date']>=RECENT_FROM]
 if len(recent)<2000:return None
 root=Path(root);root.mkdir(parents=True,exist_ok=True);path=root/'nba-context-review.json';baseline=previous['best'];catalog=definitions()
 fingerprint=hashlib.sha256((VERSION+version([r for r in recent if r['date']<CONFIRM_FROM])+json.dumps([baseline['specification'],catalog],sort_keys=True)).encode()).hexdigest()
 if path.exists():
  prior=json.loads(path.read_text())
  if prior.get('fingerprint')==fingerprint:return prior
 report={'league':'NBA','selected':baseline['name'],'final_test_start':CONFIRM_FROM,'last_date':recent[-1]['date']}
 artifact,result=review(recent,report,{'research_spec':baseline['specification'],'selected':baseline['name']},catalog)
 result.update(version=VERSION,fingerprint=fingerprint,history_from=RECENT_FROM,new_method_selected=result['status']=='challenger identified',new_candidates=len(catalog),confirmation=recent_confirmation(recent,baseline['specification'],result['best']['specification']))
 result['note']='NBA season-maturity, shared uncertainty, scoring form, venue and compressed-schedule research. Selection uses 2022–June 2025 only. Reused 2025–26 historical confirmation is not fresh independent evidence. No historical injury state is invented; live weights require the independent future gate.'
 if artifact is not None:
  artifact['history_from']=RECENT_FROM;joblib.dump(artifact,root/'nba-context-research-model.joblib')
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
 return result
