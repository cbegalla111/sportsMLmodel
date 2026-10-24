"""Public NBA team-box research. Box scores enter features only after their date."""
from collections import defaultdict,deque
from datetime import date,timezone
import math

URL='https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba/team_box/parquet/team_box_{year}.parquet'
COLUMNS=['field_goals_attempted','field_goals_made','three_point_field_goals_made','three_point_field_goals_attempted','free_throws_attempted','free_throws_made','offensive_rebounds','defensive_rebounds','total_turnovers','team_score']
METRICS=['estimated_offensive_efficiency','estimated_defensive_efficiency','effective_fg','opponent_effective_fg','possession_turnover_rate','opponent_turnover_rate','offensive_rebound_share','free_throw_attempt_rate','three_point_attempt_share','three_point_accuracy','estimated_game_possessions']
PRIORS=[115.,115.,.53,.53,.14,.14,.25,.25,.4,.36,100.]


def observations(table,known):
 """Match both source teams and scores to an independently imported final result."""
 grouped=defaultdict(list);accepted={}
 for row in table:
  eid='espn-nba-'+str(row['game_id'])
  if eid in known:grouped[eid].append(row)
 for eid,pair in grouped.items():
  if len(pair)!=2:continue
  roles={r['team_home_away']:r for r in pair}
  if set(roles)!= {'home','away'}:continue
  game=known[eid];out={};valid=True
  for side in ('home','away'):
   r=roles[side];stamp=r.get('game_date_time')
   if stamp is None or stamp.tzinfo is None or stamp.astimezone(timezone.utc).date().isoformat()!=game['date'] or r['team_display_name']!=game[side]:valid=False;break
   try:values=[float(r[c]) for c in COLUMNS]
   except (KeyError,ValueError,TypeError):valid=False;break
   if not all(math.isfinite(v) and v>=0 for v in values) or values[-1]!=float(game[side+'_score']):valid=False;break
   fga,fgm,tpm,tpa,fta,ftm,*_=values
   if not (0<=tpm<=fgm<=fga and tpm<=tpa<=fga and ftm<=fta and fga>0 and 2*fgm+tpm+ftm==values[-1]):valid=False;break
   out[side]=values
  if valid:
   try:game_metrics(out['home'],out['away'])
   except ValueError:continue
   accepted[eid]={'date':game['date'],'home':game['home'],'away':game['away'],'home_values':out['home'],'away_values':out['away']}
 return accepted


def attach(rows,boxes):
 return [dict(r,**({'_nba_box':boxes[r['event_id']]} if r['event_id'] in boxes else {})) for r in rows]


def game_metrics(own,opponent):
 import numpy as np
 fga,fgm,tpm,tpa,fta,ftm,orb,drb,tov,points=own
 ofga,ofgm,otpm,otpa,ofta,oftm,oorb,odrb,otov,opoints=opponent
 poss=.5*(fga-orb+tov+.44*fta+ofga-oorb+otov+.44*ofta)
 if not 40<=poss<=200:raise ValueError('Implausible NBA possession estimate')
 return np.array([100*points/poss,100*opoints/poss,(fgm+.5*tpm)/fga,(ofgm+.5*otpm)/ofga,tov/poss,otov/poss,orb/max(1,orb+odrb),fta/fga,tpa/fga,tpm/max(1,tpa),poss])


def box_features(rows,window=20):
 import numpy as np
 from .nba import feedback_features
 base,names=feedback_features(rows,window);names=names+[m+'_difference' for m in METRICS]+['home_box_history_available','away_box_history_available','box_history_count_difference'];history=defaultdict(lambda:deque(maxlen=window));groups=defaultdict(list);extra={}
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  def summary(team):
   records=list(history[team]);n=len(records)
   return (np.sum(records,axis=0)+5*np.array(PRIORS))/(n+5) if n else np.array(PRIORS)
  for r in group:
   h,a=r['home'],r['away'];extra[r['event_id']]=(summary(h)-summary(a)).tolist()+[float(bool(history[h])),float(bool(history[a])),float(len(history[h])-len(history[a]))]
  for r in sorted(group,key=lambda r:r['event_id']):
   box=r.get('_nba_box')
   if not box or r['outcome'] not in ('home','away'):continue
   if (box['date'],box['home'],box['away'])!=(r['date'],r['home'],r['away']):raise ValueError('NBA box identity mismatch')
   h,a=box['home_values'],box['away_values']
   if h[-1]!=float(r['home_score']) or a[-1]!=float(r['away_score']):raise ValueError('NBA box score mismatch')
   history[r['home']].append(game_metrics(h,a));history[r['away']].append(game_metrics(a,h))
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names


def fetch_history(root,rows):
 import io,json
 from pathlib import Path
 import pyarrow.parquet as pq
 from .refresh import fetch
 known={r['event_id']:r for r in rows if r['outcome'] in ('home','away')};boxes={};manifests=[]
 for year in range(2022,date.today().year+2):
  from urllib.error import HTTPError
  try:raw,manifest=fetch(root,URL.format(year=year),'NBA')
  except HTTPError as e:
   if e.code==404 and year>date.today().year:continue
   raise
  table=pq.read_table(io.BytesIO(raw),columns=['game_id','game_date_time','team_home_away','team_display_name',*COLUMNS]).to_pylist();found=observations(table,known)
  for eid,box in found.items():
   if eid in boxes and boxes[eid]!=box:raise ValueError('Conflicting public NBA box history')
   boxes[eid]=box
  manifests.append(manifest)
 report={'observations':boxes,'manifests':manifests,'matched_games':len(boxes),'description':'hoopR public ESPN team box scores, exact final result identity/score match; prior dates only. Possessions are estimates, not official pace.'}
 path=Path(root)/'nba-box-history.json'
 if path.exists():
  previous=json.loads(path.read_text()).get('observations',{})
  if any(eid in previous and previous[eid]!=box for eid,box in boxes.items()):raise ValueError('NBA box history revision needs review; cached history retained')
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,allow_nan=False));temporary.replace(path)
 return report


def blend_features(rows,window=20):
 from .nba import feedback_features
 from .rest import adjusted_features
 left,left_names=adjusted_features(*box_features(rows,10));right,right_names=adjusted_features(*feedback_features(rows,20));by_id={r['event_id']:x for r,x,_ in right}
 return [(r,x+by_id[r['event_id']],n) for r,x,n in left],left_names+['result_'+n for n in right_names]


class BoxBlend:
 def __init__(self,box,result,weight):self.box=box;self.result=result;self.weight=weight
 @staticmethod
 def inputs(X):return X[:,:37],X[:,37:]
 def predict_proba(self,X):
  import numpy as np
  a,b=self.inputs(X);p=self.weight*self.box.predict_proba(a)[:,1]+(1-self.weight)*self.result.predict_proba(b)[:,1]
  return np.column_stack((1-p,p))


def candidates():
 specs=[]
 for window in (5,10,20,40):
  for c in (.03,.3):specs.append(dict(kind='logistic',variant='context_nba_box',window=window,c=c,decay=False))
 for leaves in (3,7):specs.append(dict(kind='boost',variant='context_nba_box',window=20,leaves=leaves,decay=False))
 for gamma in (.03,.1):specs.append(dict(kind='kernel',variant='context_nba_box',window=20,gamma=gamma,c=.1,decay=False))
 for method in ('temperature','sigmoid','decision'):specs.append(dict(kind='logistic',variant='context_nba_box',window=20,c=.03,decay=False,calibrate=method,calibration_refit=True))
 for weight in (.25,.5,.75):specs.append(dict(kind='nba_box_blend',variant='context_nba_box_blend',window=20,decay=False,box_weight=weight))
 return specs


VERSION='nba-box-research-v1'


def refresh_history(root,rows):
 import json
 from pathlib import Path
 from .data import now
 path=Path(root)/'nba-box-feed.json'
 try:
  history=fetch_history(root,rows);status={'status':'ok','checked':now(),'matched_games':history['matched_games'],'error':None}
 except Exception as e:status={'status':'unavailable','checked':now(),'error':type(e).__name__+': '+str(e)}
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(status,allow_nan=False));temporary.replace(path)
 return status


def target_summary(confirmation):
 reference=confirmation['selected'] if confirmation['passed'] else confirmation['previous'];metrics=reference['validation']
 return {'target_accuracy':.7,'target_reference':reference,'candidate_accepted':bool(confirmation['passed']),'target_reached':metrics['accuracy']>=.7,'additional_correct_needed':max(0,math.ceil(.7*metrics['n'])-round(metrics['accuracy']*metrics['n']))}


def saved_research(root,rows,previous):
 """Experimental source/feature study, isolated from locked live candidates."""
 import hashlib,json
 from pathlib import Path
 from .data import version,now
 from .nba import RECENT_FROM,CONFIRM_FROM,CONFIRM_BEFORE,recent_confirmation
 from .research import review,build
 path=Path(root)/'nba-box-history.json';feed_path=Path(root)/'nba-box-feed.json'
 if not previous or not path.exists():return None
 history=json.loads(path.read_text());recent=[r for r in rows if r['date']>=RECENT_FROM]
 if len(recent)<2000:return None
 boxes=history['observations'];enriched=attach(recent,boxes);prior=previous['best']
 fingerprint=hashlib.sha256((VERSION+version([r for r in enriched if r['date']<CONFIRM_BEFORE])+json.dumps(prior['specification'],sort_keys=True)).encode()).hexdigest();result_path=Path(root)/'public-lifecycle/NBA/nba-box-review.json'
 if result_path.exists() and json.loads(result_path.read_text()).get('fingerprint')==fingerprint:result=json.loads(result_path.read_text())
 else:
  report={'league':'NBA','selected':prior['name'],'final_test_start':CONFIRM_FROM,'last_date':recent[-1]['date']}
  _,result=review(enriched,report,{'research_spec':prior['specification'],'selected':prior['name']},specifications=candidates())
  confirmation=recent_confirmation(enriched,prior['specification'],result['best']['specification'])
  # Validate the identical event/result cohort against the incumbent's report;
  # auxiliary boxes are deliberately absent from this raw-cohort fingerprint.
  left,_=build(recent,prior['specification']['window'],prior['specification']['variant']);right,_=build(enriched,result['best']['specification']['window'],result['best']['specification']['variant'])
  raw_cohort=[r for (r,_,n),(_,_,m) in zip(left,right) if CONFIRM_FROM<=r['date']<CONFIRM_BEFORE and min(n,m)>=5]
  raw_hash=version(raw_cohort)
  if raw_hash!=previous['confirmation']['cohort_sha256']:raise ValueError('NBA research confirmation cohort changed; refusing target comparison')
  result.update(box_confirmation_games=sum(r['event_id'] in boxes for r in raw_cohort),version=VERSION,fingerprint=fingerprint,confirmation=confirmation,raw_confirmation_sha256=raw_hash,**target_summary(confirmation),checked=now(),history_from=RECENT_FROM,note='Research only. All confirmation games remain in the denominator, including missing box histories. The confirmation period has been reported before; this follow-up is not an untouched test and does not promote or replace live weights. Candidate search and tuning use development dates only; confirmation supplies an acceptance gate for the single development-selected candidate.')
  result_path.parent.mkdir(parents=True,exist_ok=True);temporary=result_path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(result_path)
 result=dict(result);result.update(target_summary(result['confirmation']));result['source_status']=json.loads(feed_path.read_text()) if feed_path.exists() else {'status':'not checked','checked':None};result['source_matched_games']=history['matched_games'];result['source_manifests']=history['manifests']
 return result
