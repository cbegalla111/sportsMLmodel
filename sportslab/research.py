"""Bounded chronological model research. Archived final-test dates are never tuned."""
from collections import defaultdict,deque
from datetime import date
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .data import now,version
from .model import features,elo,scores

VERSION='sport-review-v3'
HALF_LIFE={'NBA':365,'WNBA':365,'NFL':730,'CFB':730,'MLB':180,'NHL':365,'UFC':730}

def form_features(rows,window=20):
 base,names=features(rows,window)
 names=names+['short_form_difference','opponent_strength_difference','opponent_adjusted_form_difference','form_volatility_difference','recent_workload_difference','layoff_log_difference','experience_log_difference']
 histories=defaultdict(lambda:deque(maxlen=window));activity=defaultdict(deque);last={};count=defaultdict(int);ratings=defaultdict(lambda:1500.);groups=defaultdict(list);extra={}
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  d=date.fromisoformat(day)
  def summary(team):
   h=list(histories[team]);wins=[v[0] for v in h]
   while activity[team] and (d-activity[team][0]).days>14:activity[team].popleft()
   return np.array([np.mean(wins[-3:]) if wins else .5,np.mean([v[1] for v in h]) if h else 1500.,np.mean([v[2] for v in h]) if h else 0.,np.std(wins) if wins else 0.,len(activity[team]),np.log1p(min(730,(d-last[team]).days)) if team in last else np.log1p(180),np.log1p(count[team])])
  for r in group:extra[r['event_id']]=(summary(r['home'])-summary(r['away'])).tolist()
  for r in group:
   if r['outcome'] not in ('home','away'):continue
   h,a=r['home'],r['away'];y=int(r['outcome']=='home');rh,ra=ratings[h],ratings[a]
   p=1/(1+10**(-(rh-ra+60*(1-int(r['neutral'])))/400));delta=20*(y-p)
   histories[h].append((y,ra,y-p,d));histories[a].append((1-y,rh,p-y,d));ratings[h]+=delta;ratings[a]-=delta;last[h]=last[a]=d;count[h]+=1;count[a]+=1;activity[h].append(d);activity[a].append(d)
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names

def build(rows,window=20,variant='baseline'):
 return form_features(rows,window) if variant=='form' else features(rows,window)

def definitions():
 result=[]
 for variant in ('baseline','form'):
  for window in (10,20,40):
   for c in (.03,.3):result.append({'kind':'logistic','window':window,'variant':variant,'c':c,'decay':False})
  for decay in (False,True):
   result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':decay})
  for leaves in (3,7):result.append({'kind':'boost','window':20,'variant':variant,'leaves':leaves,'decay':False})
 return result

def label(spec):
 return f"{spec['kind']}_{spec['variant']}_w{spec['window']}"+(f"_C{spec.get('c')}" if spec['kind']=='logistic' else f"_leaves{spec['leaves']}")+('_recent' if spec.get('decay') else '')

def fit(spec,X,y,days,league):
 if spec['kind']=='elo':return None
 weights=None
 if spec.get('decay'):
  latest=date.fromisoformat(max(days));age=np.array([(latest-date.fromisoformat(d)).days for d in days]);weights=np.exp2(-age/HALF_LIFE[league])
 if spec['kind']=='boost':
  m=HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=spec.get('leaves',7),l2_regularization=20,learning_rate=.04,random_state=42);m.fit(X,y,sample_weight=weights)
 else:
  m=make_pipeline(StandardScaler(),LogisticRegression(C=spec.get('c',.1),max_iter=800,random_state=42));kwargs={'logisticregression__sample_weight':weights} if weights is not None else {};m.fit(X,y,**kwargs)
 return m

def predict(m,X):return elo(X) if m is None else m.predict_proba(X)[:,1]

def incumbent_spec(report,champion=None):
 if champion and champion.get('research_spec'):return dict(champion['research_spec'])
 selected=report['selected'];parts=selected.split('_w');window=int(parts[-1].split('_')[0]);kind='elo' if selected.startswith('elo') else 'boost' if selected.startswith('boost') else 'logistic'
 return {'kind':kind,'window':window,'variant':'baseline','c':.01 if 'strong' in selected else 1. if 'weak' in selected else .1,'leaves':7,'decay':False,'legacy':True}

def review(rows,report,champion=None):
 """Compare on identical expanding development dates; return a deployable challenger."""
 rows=[r for r in rows if r['outcome'] in ('home','away')];league=report['league'];cut=report['final_test_start'];dev=[r for r in rows if r['date']<cut]
 days=sorted({r['date'] for r in dev})
 if len(dev)<200 or len(days)<40:raise ValueError('Not enough pre-test development history for a comparable review')
 # Every contender uses these exact date blocks and the same warm-up cohort.
 folds=[]
 for left,right in ((.4,.6),(.6,.8),(.8,1.0)):
  start=days[int(len(days)*left)];end=days[int(len(days)*right)] if right<1 else cut;folds.append((start,end))
 specs=[incumbent_spec(report,champion),*definitions()];cache={};results=[];predictions=[];ds=np.array([r['date'] for r in dev]);y=np.array([int(r['outcome']=='home') for r in dev]);min_history=3 if league=='UFC' else 5
 for spec in specs:
  key=(spec['window'],spec['variant'])
  if key not in cache:cache[key]=build(dev,*key)
 cohort=np.logical_and.reduce([np.array([v[2]>=min_history for v in built]) for built,_ in cache.values()])
 for i,spec in enumerate(specs):
  built,names=cache[(spec['window'],spec['variant'])];X=np.array([v[1] for v in built]);blocks=[];p_all=[];y_all=[];d_all=[]
  for start,end in folds:
   tr=(ds<start)&cohort;va=(ds>=start)&(ds<end)&cohort
   if va.sum()<20 or len(set(y[tr]))<2:raise ValueError('An expanding fold lacks sufficient comparable observations')
   if spec.get('legacy') and spec['kind']!='elo':
    from .model import estimator
    kind='boost' if spec['kind']=='boost' else 'logistic_strong' if spec['c']==.01 else 'logistic_weak' if spec['c']==1 else 'logistic';m=estimator(kind);m.fit(X[tr],y[tr])
   else:m=fit(spec,X[tr],y[tr],list(ds[tr]),league)
   p=predict(m,X[va]);blocks.append(dict(scores(y[va],p),train_end=str(max(ds[tr])),validation_start=str(min(ds[va])),validation_end=str(max(ds[va]))));p_all.extend(p);y_all.extend(y[va]);d_all.extend(ds[va])
  aggregate=scores(np.array(y_all),np.array(p_all));results.append({'name':champion.get('selected',report['selected']) if i==0 and champion else report['selected'] if i==0 else label(spec),'specification':spec,'folds':blocks,'validation':aggregate});predictions.append((np.array(y_all),np.array(p_all),d_all))
 incumbent=results[0];eligible=[i for i,r in enumerate(results[1:],1) if r['validation']['accuracy']>=incumbent['validation']['accuracy'] and r['validation']['brier']<=incumbent['validation']['brier']]
 selected=min(eligible,key=lambda i:results[i]['validation']['log_loss']) if eligible else 0
 if results[selected]['validation']['log_loss']>=incumbent['validation']['log_loss']:selected=0
 chosen=results[selected];spec=chosen['specification'];built,names=build(rows,spec['window'],spec['variant']);warm=np.array([v[2]>=min_history for v in built]);X=np.array([v[1] for v in built]);yy=np.array([int(v[0]['outcome']=='home') for v in built]);all_days=np.array([v[0]['date'] for v in built])
 if spec.get('legacy') and spec['kind']!='elo':
  from .model import estimator
  kind='boost' if spec['kind']=='boost' else 'logistic_strong' if spec['c']==.01 else 'logistic_weak' if spec['c']==1 else 'logistic';m=estimator(kind);m.fit(X[warm],yy[warm])
 else:m=fit(spec,X[warm],yy[warm],list(all_days[warm]),league)
 artifact={'model':m,'research_spec':dict(spec),'window':spec['window'],'variant':spec['variant'],'extra':False,'names':names,'digest':version(rows),'training_event_ids':[r['event_id'] for r in rows],'last_date':rows[-1]['date'],'league':league,'neutral_variation':len(np.unique(X[warm,1]))>1,'selected':chosen['name'],'refitted':now()}
 result={'version':VERSION,'checked':now(),'league':league,'development_sha256':version(dev),'development_through':dev[-1]['date'],'excluded_final_test_from':cut,'selected':chosen['name'],'incumbent':incumbent,'best':chosen,'candidates':results,'candidate_count':len(results)-1,'accuracy_gain':chosen['validation']['accuracy']-incumbent['validation']['accuracy'],'log_loss_gain':incumbent['validation']['log_loss']-chosen['validation']['log_loss'],'status':'challenger identified' if selected else 'incumbent specification retained','note':'Expanding development backtests only. Candidate selection gains are optimistic; no new independent test or production improvement is claimed. Original final-test dates were excluded. Production promotion still requires the separate prospective loss-review gate.'}
 return artifact,result

def saved_review(root,rows,report,champion=None):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);path=root/'research-review.json';fingerprint=hashlib.sha256((VERSION+version([r for r in rows if r['date']<report['final_test_start']])+json.dumps(incumbent_spec(report,champion),sort_keys=True)).encode()).hexdigest()
 if path.exists():
  prior=json.loads(path.read_text())
  if prior.get('fingerprint')==fingerprint:return prior
 artifact,result=review(rows,report,champion);result['fingerprint']=fingerprint
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
 joblib.dump(artifact,root/'research-challenger.joblib')
 return result
