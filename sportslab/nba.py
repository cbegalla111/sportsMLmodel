"""Causal NBA feedback signals: all of a date's inputs precede its outcomes."""
from collections import defaultdict
from datetime import date
import math


def feedback_features(rows,window=20):
 from .research import bayesian_features
 if not rows or any(r['league']!='NBA' for r in rows):raise ValueError('NBA feedback features require NBA results')
 base,names=bayesian_features(rows,window)
 names=names+['adaptive_margin_strength_difference','unexpected_win_fast_difference','unexpected_margin_fast_difference','unexpected_win_momentum_difference','prediction_error_variance_difference','prediction_loss_difference']
 # Per-team online estimates. Outcome errors use y-p, so a confidently wrong
 # forecast moves strength more than an expected win. Both wins and losses count.
 states=defaultdict(lambda:[0.,0.,0.,0.,0.,0.]);seasons={};groups=defaultdict(list);extra={}
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  year=date.fromisoformat(day).year+(date.fromisoformat(day).month>=7)
  teams={r[k] for r in group for k in ('home','away')}
  for team in teams:
   elapsed=max(0,year-seasons.get(team,year))
   if elapsed:states[team]=[v*.7**elapsed for v in states[team]]
   seasons[team]=year
  changes=defaultdict(list)
  for r in group:
   h,a=r['home'],r['away'];hs,aws=states[h],states[a]
   extra[r['event_id']]=[hs[0]-aws[0],hs[1]-aws[1],hs[2]-aws[2],(hs[1]-hs[3])-(aws[1]-aws[3]),hs[4]-aws[4],hs[5]-aws[5]]
   if r['outcome'] not in ('home','away'):continue
   margin_prior=hs[0]-aws[0]+(3. if r['neutral']=='0' else 0.)
   p=1/(1+math.exp(-max(-30.,min(30.,margin_prior/12.))))
   residual=int(r['outcome']=='home')-p
   margin_error=max(-30.,min(30.,float(r['home_score'])-float(r['away_score'])-margin_prior))
   y=int(r['outcome']=='home');loss=-(y*math.log(max(p,1e-12))+(1-y)*math.log(max(1-p,1e-12)))
   changes[h].append((residual,margin_error,loss));changes[a].append((-residual,-margin_error,loss))
  # Batch same-date updates make state independent of within-day row ordering.
  for team,errors in changes.items():
   win=sum(e[0] for e in errors)/len(errors);margin=sum(e[1] for e in errors)/len(errors);loss=sum(e[2] for e in errors)/len(errors);square=sum(e[0]**2 for e in errors)/len(errors)
   old=states[team];states[team]=[old[0]+.08*margin,.8*old[1]+.2*win,.8*old[2]+.2*margin,.95*old[3]+.05*win,.9*old[4]+.1*square,.9*old[5]+.1*loss]
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names


def later_era_audit(rows,previous,selected,archive_end):
 """Audit two already-fixed specifications on later complete NBA seasons."""
 import numpy as np
 from .research import build,fit,predict,quality_scores,InsufficientCalibration
 today=date.today();end_year=today.year if today.month>=7 else today.year-1
 end=f'{end_year}-07-01';start=f'{end_year-3}-07-01'
 if start<=archive_end:return None
 audit_rows=[r for r in rows if r['date']<end]
 if not audit_rows or audit_rows[-1]['date']<f'{end_year}-04-01':return None
 ds=np.array([r['date'] for r in audit_rows]);y=np.array([int(r['outcome']=='home') for r in audit_rows]);targets=np.array([[float(r['home_score']),float(r['away_score'])] for r in audit_rows]);cache={}
 for spec in (previous,selected):
  key=(spec['window'],spec['variant'])
  if key not in cache:cache[key]=build(audit_rows,*key)
 cohort=np.logical_and.reduce([np.array([n>=5 for _,_,n in built]) for built,_ in cache.values()])
 models=[]
 for spec in (previous,selected):
  built,names=cache[(spec['window'],spec['variant'])];X=np.array([x for _,x,_ in built]);evalX=X
  if not spec['variant'].startswith('context_') and spec['variant'] not in ('rest_guard','no_rest'):
   from .rest import adjusted_features
   corrected,_=adjusted_features(built,names,'recovery_only');evalX=np.array([x for _,x,_ in corrected])
  blocks=[];actual=[];prob=[]
  for year in range(end_year-3,end_year):
   first=f'{year}-07-01';last=f'{year+1}-07-01';tr=(ds<first)&cohort;va=(ds>=first)&(ds<last)&cohort
   if tr.sum()<700 or va.sum()<100:return None
   try:m=fit(spec,X[tr],y[tr],list(ds[tr]),'NBA',targets[tr])
   except InsufficientCalibration:return None
   p=predict(m,evalX[va]);blocks.append(dict(quality_scores(y[va],p),train_end=str(max(ds[tr])),validation_start=str(min(ds[va])),validation_end=str(max(ds[va]))));actual.extend(y[va]);prob.extend(p)
  models.append({'specification':spec,'validation':quality_scores(np.array(actual),np.array(prob)),'folds':blocks})
 return {'from':start,'before':end,'previous':models[0],'selected':models[1],'note':'Later-season audit of two specifications already selected on the older development period. Refit on preceding dates only; no specification selection or promotion uses this audit. Original archived test metrics remain sealed.'}


def hybrid_features(rows,window=20):
 from .research import form_features
 base,names=feedback_features(rows,window);form,form_names=form_features(rows,window)
 lookup={r['event_id']:x[5:] for r,x,_ in form}
 return [(r,x+lookup[r['event_id']],n) for r,x,n in base],names+form_names[5:]


class FeedbackBlend:
 """Fixed average of two separately trained, complementary input views."""
 def __init__(self,feedback,form,weight):self.feedback=feedback;self.form=form;self.weight=weight
 @staticmethod
 def inputs(X):
  import numpy as np
  return np.column_stack((X[:,:21],X[:,-2:])),np.column_stack((X[:,:5],X[:,21:28],X[:,-2:]))
 def predict_proba(self,X):
  import numpy as np
  feedback,form=self.inputs(X);p=self.weight*self.feedback.predict_proba(feedback)[:,1]+(1-self.weight)*self.form.predict_proba(form)[:,1]
  return np.column_stack((1-p,p))


RECENT_VERSION='nba-recent-v1-causal-feedback'
RECENT_FROM='2022-01-01'
CONFIRM_FROM='2025-07-01'
CONFIRM_BEFORE='2026-07-01'


def recent_confirmation(rows,previous,selected):
 import numpy as np
 from .data import version
 from .research import build,fit,predict,quality_scores
 rows=[r for r in rows if RECENT_FROM<=r['date']<CONFIRM_BEFORE]
 ds=np.array([r['date'] for r in rows]);y=np.array([int(r['outcome']=='home') for r in rows]);targets=np.array([[float(r['home_score']),float(r['away_score'])] for r in rows]);specs=(previous,selected);views=[build(rows,s['window'],s['variant']) for s in specs]
 warm=np.logical_and.reduce([np.array([n>=5 for _,_,n in b]) for b,_ in views]);tr=(ds<CONFIRM_FROM)&warm;te=(ds>=CONFIRM_FROM)&warm
 if tr.sum()<700 or te.sum()<100:return None
 checks=[]
 for spec,(built,names) in zip(specs,views):
  X=np.array([x for _,x,_ in built]);evalX=X
  if not spec['variant'].startswith('context_') and spec['variant'] not in ('rest_guard','no_rest'):
   from .rest import adjusted_features
   corrected,_=adjusted_features(built,names,'recovery_only');evalX=np.array([x for _,x,_ in corrected])
  m=fit(spec,X[tr],y[tr],list(ds[tr]),'NBA',targets[tr]);checks.append({'specification':spec,'validation':quality_scores(y[te],predict(m,evalX[te]))})
 old,new=[c['validation'] for c in checks]
 return {'from':CONFIRM_FROM,'before':CONFIRM_BEFORE,'previous':checks[0],'selected':checks[1],'train_end':str(max(ds[tr])),'cohort_sha256':version([r for r,keep in zip(rows,te) if keep]),'passed':bool(new['accuracy']>=old['accuracy'] and new['log_loss']<old['log_loss'] and new['brier']<=old['brier']),'note':'Historical confirmation of specifications selected on pre-July 2025 results, both trained on the same recent history. The current season and original archived test are excluded. This is not prospective promotion evidence.'}


def saved_recent_review(root,rows,older_review):
 """Separate modern research period; never reselect on historical confirmation."""
 import hashlib,json,joblib
 from pathlib import Path
 from .data import version
 from .research import review,review_version
 recent=[r for r in rows if r['date']>=RECENT_FROM]
 if not older_review or len(recent)<2000 or recent[-1]['date']<'2026-06-01':return None
 previous=older_review['best'];development=[r for r in recent if r['date']<CONFIRM_FROM]
 if len(development)<1000:return None
 fingerprint=hashlib.sha256((RECENT_VERSION+review_version('NBA')+version(development)+json.dumps(previous['specification'],sort_keys=True)).encode()).hexdigest();path=Path(root)/'nba-recent-review.json'
 if path.exists():
  cached=json.loads(path.read_text())
  if cached.get('fingerprint')==fingerprint and (Path(root)/'nba-recent-challenger.joblib').exists():return cached
 report={'league':'NBA','selected':previous['name'],'final_test_start':CONFIRM_FROM,'last_date':recent[-1]['date']}
 artifact,result=review(recent,report,{'research_spec':previous['specification'],'selected':previous['name']})
 result.update(version=RECENT_VERSION,fingerprint=fingerprint,history_from=RECENT_FROM,confirmation=recent_confirmation(recent,previous['specification'],result['best']['specification']),note='Recent-data research is separate from the original archived test. Selection uses 2022 through June 2025 only; subsequent completed-season confirmation does not select candidates. Development gains remain optimistic. No live weights change without the independent prospective gate.')
 if artifact is None:return result
 artifact['history_from']=RECENT_FROM
 joblib.dump(artifact,Path(root)/'nba-recent-challenger.joblib')
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
 return result


def refit_recent_candidate(root,rows):
 """Refit the frozen recent specification on fresh results after a real miss."""
 import joblib,numpy as np
 from pathlib import Path
 from .data import version,now
 from .research import build,fit
 artifact=joblib.load(Path(root)/'nba-recent-challenger.joblib');spec=artifact['research_spec'];recent=[r for r in rows if r['date']>=artifact['history_from']];built,names=build(recent,spec['window'],spec['variant']);warm=np.array([n>=5 for _,_,n in built]);X=np.array([x for _,x,_ in built]);y=np.array([int(r['outcome']=='home') for r in recent]);targets=np.array([[float(r['home_score']),float(r['away_score'])] for r in recent]);ds=np.array([r['date'] for r in recent])
 artifact.update(model=fit(spec,X[warm],y[warm],list(ds[warm]),'NBA',targets[warm]),names=names,digest=version(recent),training_event_ids=[r['event_id'] for r in recent],last_date=recent[-1]['date'],neutral_variation=len(np.unique(X[warm,1]))>1,refitted=now())
 return artifact
