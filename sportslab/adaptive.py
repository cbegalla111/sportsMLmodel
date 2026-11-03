"""Bounded, causal error-adaptive research; final tests never select specifications."""
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import joblib

VERSION='adaptive-error-review-v1'
# Fixed sport units describe result scale; predictive coefficients are learned.
SCALE={'NBA':12.,'WNBA':10.,'NFL':14.,'CFB':18.,'MLB':3.,'NHL':2.,'UFC':1.}
ADVANTAGE={'NBA':3.,'WNBA':2.5,'NFL':2.,'CFB':3.,'MLB':.2,'NHL':.2,'UFC':0.}

def feedback_features(rows,window=20):
 from .research import bayesian_features
 from .model import season
 base,names=bayesian_features(rows,window);league=rows[0]['league'];scale=SCALE[league]
 names=names+['adaptive_strength_difference','fast_surprise_difference','slow_surprise_difference','surprise_momentum_difference','error_variance_difference','recent_probability_loss_difference','adaptive_margin_difference']
 states=defaultdict(lambda:[0.,0.,0.,.25,math.log(2),0.]);seasons={};groups=defaultdict(list);extra={}
 for row in rows:groups[row['date']].append(row)
 for day,group in sorted(groups.items()):
  current=int(season(league,day));teams={r[k] for r in group for k in ('home','away')}
  for team in teams:
   elapsed=0 if league=='UFC' else max(0,current-seasons.get(team,current))
   if elapsed:
    old=states[team];decay=.75**elapsed
    states[team]=[old[0]*decay,old[1]*decay,old[2]*decay,.25+(old[3]-.25)*decay,math.log(2)+(old[4]-math.log(2))*decay,old[5]*decay]
   seasons[team]=current
  changes=defaultdict(list)
  for row in group:
   home,away=row['home'],row['away'];h,a=states[home],states[away]
   extra[row['event_id']]=[h[0]-a[0],h[1]-a[1],h[2]-a[2],(h[1]-h[2])-(a[1]-a[2]),h[3]-a[3],h[4]-a[4],h[5]-a[5]]
   if row['outcome'] not in ('home','away'):continue
   logit=h[0]-a[0]+(ADVANTAGE[league]/scale if row['neutral']=='0' else 0.)
   p=1/(1+math.exp(-max(-20.,min(20.,logit))));y=int(row['outcome']=='home');residual=y-p
   loss=-(y*math.log(p)+(1-y)*math.log1p(-p))
   # UFC 1-0 outcomes are encodings, not real margins.
   margin=0. if league=='UFC' else max(-3.,min(3.,(float(row['home_score'])-float(row['away_score']))/scale))-logit
   changes[home].append((residual,loss,margin));changes[away].append((-residual,loss,-margin))
  # Every same-date feature precedes all outcomes on that date, including doubleheaders.
  for team,errors in changes.items():
   n=len(errors);residual=sum(e[0] for e in errors)/n;loss=sum(e[1] for e in errors)/n;margin=sum(e[2] for e in errors)/n;square=sum(e[0]**2 for e in errors)/n;old=states[team]
   rate=.08+.16*min(1.,math.sqrt(old[3]))
   states[team]=[max(-4.,min(4.,old[0]+rate*residual)),.75*old[1]+.25*residual,.95*old[2]+.05*residual,.9*old[3]+.1*square,.9*old[4]+.1*loss,.85*old[5]+.15*margin]
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names

def definitions():
 result=[{'kind':'logistic','variant':'context_feedback','window':window,'c':c,'decay':decay} for window in (10,20) for c in (.03,.3,1.) for decay in (False,True)]
 for window in (10,20):
  for method in ('temperature','sigmoid','decision'):result.append({'kind':'logistic','variant':'context_feedback','window':window,'c':.3,'decay':False,'calibrate':method,'calibration_refit':True})
 for weight in (.25,.5,.75):result.append({'kind':'adaptive_blend','variant':'context_feedback','window':20,'c':.3,'decay':False,'adaptive_weight':weight})
 return result

def saved_review(root,rows,report,champion,previous):
 from .research import review,incumbent_spec
 from .data import version
 root=Path(root);root.mkdir(parents=True,exist_ok=True);path=root/'adaptive-review.json';specs=definitions();old_spec=(previous or {}).get('best',{}).get('specification')
 reference=dict(champion,research_spec=old_spec,selected=previous['best']['name']) if old_spec else champion
 fingerprint=hashlib.sha256((VERSION+report['final_test_start']+version([r for r in rows if r['date']<report['final_test_start']])+json.dumps([incumbent_spec(report,champion),old_spec,specs],sort_keys=True)).encode()).hexdigest()
 if path.exists():
  prior=json.loads(path.read_text())
  if prior.get('fingerprint')==fingerprint:return prior
 artifact,result=review(rows,report,reference,specs);result.update(version=VERSION,fingerprint=fingerprint,new_candidates=len(specs),production_reference=incumbent_spec(report,champion),benchmark_id=report.get('id'),benchmark_sha256=report.get('dataset_sha256'))
 result['new_method_selected']=result['status']=='challenger identified' and result['best']['specification']['variant']=='context_feedback'
 result['note']='Twenty-one fixed adaptive candidates against the prior development winner, compared on shared expanding pre-final-test dates. Selection is optimistic; only the separate future gate can change production weights.'
 # Cached development evidence is fixed; locking a trial refits its frozen specification on latest data.
 if artifact is not None and result['new_method_selected']:joblib.dump(artifact,root/'adaptive-research-model.joblib')
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
 return result

def trial(root,state,rows,report,champion,champion_path,research,losses):
 from .data import now
 from .research import review
 from .lifecycle import probabilities,gate,confirmation_after
 import numpy as np
 root=Path(root);active=state.get('adaptive_trial');message=None
 digest=hashlib.sha256(champion_path.read_bytes()).hexdigest()
 if active and active['status']=='collecting evidence':
  if digest!=active['reference_sha256']:
   active['status']='superseded by champion change';return champion,None
  challenger=joblib.load(root/'adaptive-trial-model.joblib');reference=joblib.load(root/'adaptive-trial-reference.joblib')
  old,rr=probabilities(reference,rows,confirmation_after(active));new,_=probabilities(challenger,rows,confirmation_after(active));ids=sorted(set(old)&set(new),key=lambda k:(rr[k]['date'],k))
  decision=gate(np.array([int(rr[k]['outcome']=='home') for k in ids]),np.array([old[k] for k in ids]),np.array([new[k] for k in ids]),[rr[k]['date'] for k in ids]);active['confirmation']=decision
  if decision['status']=='collecting evidence':return champion,None
  active['status']=decision['status'];state['reviews'].append(dict(decision,reviewed=now(),trial_after=active['after'],source=VERSION))
  if decision['promote']:
   joblib.dump(champion,root/'previous-champion.joblib');temporary=champion_path.with_suffix('.tmp');joblib.dump(challenger,temporary);temporary.replace(champion_path)
   if state.get('trial'):state.setdefault('superseded_trials',[]).append({'trial':state['trial'],'at':now(),'reason':'adaptive candidate passed independent gate'})
   state['trial']=None;state['confirmation']=None;state['consumed_losses']=losses
   return challenger,'Error-adaptive model promoted after all independent improvement checks.'
  return champion,None
 focus=(research or {}).get('nba_focus_research')
 modern=focus if focus and focus.get('new_method_selected') and (focus.get('confirmation') or {}).get('passed') else (research or {}).get('recent_data_research')
 research=modern if modern and modern.get('new_method_selected') and (modern.get('confirmation') or {}).get('passed') else research
 if not research or not research.get('new_method_selected') or losses<=state.get('adaptive_consumed_losses',0):return champion,None
 # Refit only the specification fixed by development selection. No future result selects its weights.
 history_from=research.get('history_from')
 training=[r for r in rows if r['date']>=history_from] if history_from else rows
 trial_report={'league':report['league'],'selected':research['incumbent']['name'],'final_test_start':research['excluded_final_test_from'],'last_date':training[-1]['date']} if history_from else report
 reference={'research_spec':research['incumbent']['specification'],'selected':research['incumbent']['name']} if history_from else champion
 candidate,refit=review(training,trial_report,reference,[research['best']['specification']])
 if candidate is not None and history_from:candidate['history_from']=history_from
 state['adaptive_consumed_losses']=losses
 if candidate is None or candidate['variant'] not in ('context_feedback','context_nba_context','context_nba_feedback'):return champion,None
 if active:state.setdefault('adaptive_trial_history',[]).append(active)
 joblib.dump(candidate,root/'adaptive-trial-model.joblib');joblib.dump(champion,root/'adaptive-trial-reference.joblib')
 created=now()
 state['adaptive_trial']={'version':VERSION,'created':created,'after':max(rows[-1]['date'],created[:10]),'selected':candidate['selected'],'reference_sha256':digest,'status':'collecting evidence','development_fingerprint':research['fingerprint']}
 return champion,'Error-adaptive challenger locked after a saved loss; collecting independent evidence.'

def saved_recent_review(root,rows,previous):
 """Fixed modern NBA development period; historical confirmation is never searched."""
 from .nba import RECENT_FROM,CONFIRM_FROM,recent_confirmation
 from .research import review
 from .data import version
 if not previous:return None
 recent=[r for r in rows if r['date']>=RECENT_FROM]
 if len(recent)<2000:return None
 baseline=previous['best'];root=Path(root);root.mkdir(parents=True,exist_ok=True);path=root/'adaptive-recent-review.json'
 fingerprint=hashlib.sha256((VERSION+version([r for r in recent if r['date']<CONFIRM_FROM])+json.dumps([baseline['specification'],definitions()],sort_keys=True)).encode()).hexdigest()
 if path.exists():
  cached=json.loads(path.read_text())
  if cached.get('fingerprint')==fingerprint:return cached
 report={'league':'NBA','selected':baseline['name'],'final_test_start':CONFIRM_FROM,'last_date':recent[-1]['date']}
 artifact,result=review(recent,report,{'research_spec':baseline['specification'],'selected':baseline['name']},definitions())
 result.update(version=VERSION,fingerprint=fingerprint,history_from=RECENT_FROM,new_method_selected=result['status']=='challenger identified' and result['best']['specification']['variant']=='context_feedback',confirmation=recent_confirmation(recent,baseline['specification'],result['best']['specification']))
 result['note']='Modern NBA search uses only 2022–June 2025 development dates. The already-reused 2025–26 historical confirmation is evaluated only for the development-selected specification; it is not fresh independent evidence. No production promotion without new future checks.'
 if artifact is not None:
  artifact['history_from']=RECENT_FROM;joblib.dump(artifact,root/'adaptive-recent-model.joblib')
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
 return result
