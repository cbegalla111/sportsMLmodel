import copy
import json
import math
from collections import defaultdict, deque
from datetime import date
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss, brier_score_loss, accuracy_score, roc_auc_score
from .data import FEATURES, load, now, version

BUDGET='10 fixed candidates, 3 expanding date-block folds; no random split, no tuning on final 20% of dates; single CPU.'

def features(rows, window=20, extra=False):
 history=defaultdict(lambda:deque(maxlen=window)); ratings=defaultdict(lambda:1500.); last={}; output=[]
 names=['elo_difference','home_advantage','win_rate_difference','scoring_margin_difference','rest_difference']
 if extra: names += [f+'_difference' for f in FEATURES[rows[0]['league']]]
 grouped=defaultdict(list)
 for r in rows: grouped[r['date']].append(r)
 for day,group in sorted(grouped.items()):
  for r in group:
   h,a=r['home'],r['away']; d=date.fromisoformat(day)
   def avg(t,k,default): return float(np.mean([v[k] for v in history[t]])) if history[t] else default
   rest=lambda t:min(730 if r['league']=='UFC' else 14,(d-last[t]).days) if t in last else (180 if r['league']=='UFC' else 7)
   x=[ratings[h]-ratings[a],1-int(r['neutral']),avg(h,0,.5)-avg(a,0,.5),avg(h,1,0)-avg(a,1,0),rest(h)-rest(a)]
   if extra: x += [float(r['home_'+f])-float(r['away_'+f]) for f in FEATURES[r['league']]]
   output.append((r,x,min(len(history[h]),len(history[a]))))
  # Every game's inputs on a date precede every outcome on that date.
  for r in group:
   if r['outcome'] not in ('home','away'): continue
   h,a=r['home'],r['away']; y=int(r['outcome']=='home'); margin=float(r['home_score'])-float(r['away_score'])
   p=1/(1+10**(-(ratings[h]-ratings[a]+60*(1-int(r['neutral'])))/400))
   delta=20*(y-p); ratings[h]+=delta; ratings[a]-=delta
   history[h].append((y,margin)); history[a].append((1-y,-margin)); last[h]=last[a]=date.fromisoformat(day)
 return output,names

def estimator(kind):
 if kind=='boost': return HistGradientBoostingClassifier(max_iter=60,max_leaf_nodes=7,l2_regularization=10,learning_rate=.05,random_state=42)
 return make_pipeline(StandardScaler(),LogisticRegression(C={'logistic_strong':.01,'logistic_weak':1.}.get(kind,.1),max_iter=500,random_state=42))

def elo(X): return 1/(1+10**(-(X[:,0]+60*X[:,1])/400))

def scores(y,p):
 p=np.clip(p,1e-6,1-1e-6)
 return {'n':len(y),'log_loss':float(log_loss(y,p,labels=[0,1])),'brier':float(brier_score_loss(y,p)),'accuracy':float(accuracy_score(y,p>=.5)),'roc_auc':float(roc_auc_score(y,p)) if len(set(y))==2 else None}

def season(league,day):
 d=date.fromisoformat(day)
 if league in ('NBA','WNBA','NHL') and league!='WNBA': return str(d.year+(d.month>=7))
 if league in ('NFL','CFB'): return str(d.year-(d.month<3))
 return str(d.year)

def evaluate(y,p,dates,league='NBA'):
 result=scores(y,p); result['calibration']=[]
 for lo in np.arange(0,1,.1):
  ix=(p>=lo)&(p<lo+.100000001)
  # Half-open bins avoid duplicate edge observations.
  ix=(p>=lo)&(p<(lo+.1 if lo<.9 else 1.000001))
  if ix.any(): result['calibration'].append({'band':[round(float(lo),1),round(float(lo+.1),1)],'n':int(ix.sum()),'predicted':float(p[ix].mean()),'observed':float(y[ix].mean())})
 result['by_year']={yr:scores(y[np.array([d[:4]==yr for d in dates])],p[np.array([d[:4]==yr for d in dates])]) for yr in sorted({d[:4] for d in dates})}
 # Resample whole calendar weeks to retain within-week dependence.
 weeks=np.array([date.fromisoformat(d).strftime('%G-%V') for d in dates]); unique=np.unique(weeks); rng=np.random.default_rng(42); vals=[]
 for _ in range(200):
  ix=np.concatenate([np.where(weeks==w)[0] for w in rng.choice(unique,len(unique),replace=True)])
  vals.append(scores(y[ix],p[ix])['brier'])
 result['by_season']={yr:scores(y[np.array([season(league,d)==yr for d in dates])],p[np.array([season(league,d)==yr for d in dates])]) for yr in sorted({season(league,d) for d in dates})}
 result['brier_week_block_bootstrap_95']=[float(x) for x in np.quantile(vals,[.025,.975])]
 result['interval_note']='200 calendar-week block bootstrap samples of fixed final-test predictions; approximate performance uncertainty, not a game probability interval.'
 return result

def train(db,root,league):
 rows=[r for r in load(db,league) if r['outcome'] in ('home','away')]
 digest=version(rows); eid=league+'-'+digest[:16]
 prior=db.execute('SELECT payload FROM experiments WHERE league=? ORDER BY created LIMIT 1',(league,)).fetchone()
 if prior:
  result=json.loads(prior[0])
  if result['dataset_sha256']!=digest: raise ValueError('This league already has a sealed final test. Refresh the frozen model; do not reselect against overlapping held-out data.')
  return result
 days=sorted({r['date'] for r in rows})
 if len(rows)<700 or len(days)<100: raise ValueError('At least 700 decisive results across 100 dates are required; no fitted prediction available.')
 cutoff=days[int(len(days)*.8)]; dev_days=[d for d in days if d<cutoff]
 definitions=[('elo',20,False),('logistic',10,False),('logistic',20,False),('logistic',40,False),('logistic_strong',20,False),('logistic_weak',20,False),('logistic',20,True),('boost',10,False),('boost',20,False),('boost',40,False)]
 candidates=[]; caches={}
 for kind,window,extra in definitions:
  label=f'{kind}_w{window}'+('_sport_features' if extra else '')
  if extra and not all(all(s+'_'+f in r for f in FEATURES[league] for s in ('home','away')) for r in rows):
   candidates.append({'name':label,'status':'skipped','reason':'Complete timestamped sport-specific features unavailable'}); continue
  built,names=features(rows,window,extra); X=np.array([v[1] for v in built]); y=np.array([int(v[0]['outcome']=='home') for v in built]); ds=np.array([v[0]['date'] for v in built]); warm=np.array([v[2]>=(3 if league=='UFC' else 5) for v in built]); folds=[]
  for left,right in ((.4,.6),(.6,.8),(.8,1.0)):
   start=dev_days[int(len(dev_days)*left)]; end=dev_days[min(len(dev_days)-1,int(len(dev_days)*right))]
   tr=(ds<start)&warm; va=(ds>=start)&(ds<end)&warm
   if len(set(y[tr]))<2 or va.sum()<20: raise ValueError('Insufficient classes or fold observations')
   if kind=='elo': p=elo(X[va])
   else:
    m=estimator(kind); m.fit(X[tr],y[tr]); p=m.predict_proba(X[va])[:,1]
   folds.append(dict(scores(y[va],p),train_end=str(max(ds[tr])),validation_start=str(min(ds[va])),validation_end=str(max(ds[va]))))
  candidates.append({'name':label,'status':'completed','folds':folds,'mean_log_loss':float(np.mean([f['log_loss'] for f in folds]))})
  caches[label]=(kind,window,extra,X,y,ds,warm,names)
 selected=min([c for c in candidates if c['status']=='completed'],key=lambda c:c['mean_log_loss'])['name']
 kind,window,extra,X,y,ds,warm,names=caches[selected]; tr=(ds<cutoff)&warm; te=(ds>=cutoff)&warm
 m=None
 if kind!='elo': m=estimator(kind); m.fit(X[tr],y[tr])
 p=elo(X[te]) if m is None else m.predict_proba(X[te])[:,1]
 result={'id':eid,'league':league,'created':now(),'dataset_sha256':digest,'n_rows':len(rows),'first_date':rows[0]['date'],'last_date':rows[-1]['date'],'final_test_start':cutoff,'budget':BUDGET,'selected':selected,'candidates':candidates,'test':evaluate(y[te],p,list(ds[te]),league),'baseline_test':scores(y[te],elo(X[te])),'feature_names':names,'outcome_rules':'Conditional on a decisive eventual winner, including overtime. Draws and no contests excluded; this is NOT an unconditional win probability or a sportsbook settlement forecast.','calibration':'No post-hoc calibration; reliability measured on held-out data.','limitations':['Result-only baseline; no confirmed injuries, starters, travel, weather or lineups.','Score margin is not possession-adjusted efficiency.','Pre-event feature timestamps are uploader assertions, not independently verified.','Historical performance does not establish present-day calibration.']}
 # Final test is now sealed; full-data refit is only for future/scenario inference, never reported as test performance.
 if kind!='elo': m=estimator(kind); m.fit(X[warm],y[warm])
 artifact={'model':m,'window':window,'extra':extra,'names':names,'digest':digest,'training_event_ids':[r['event_id'] for r in rows],'last_date':rows[-1]['date'],'league':league,'neutral_variation':len(np.unique(X[warm,1]))>1}
 dest=Path(root)/'models'; dest.mkdir(exist_ok=True); joblib.dump(artifact,dest/(eid+'.joblib'))
 with db: db.execute('INSERT INTO experiments VALUES(?,?,?,?)',(eid,league,now(),json.dumps(result)))
 return result

def model_features(rows,window=20,extra=False,variant='baseline'):
 if variant=='baseline':return features(rows,window,extra)
 if extra:raise ValueError('Combined uploaded and form features are not validated')
 if variant!='form':raise ValueError('Unknown model feature variant')
 from .research import form_features
 return form_features(rows,window)

def fixture_inputs(rows,fixtures,window,extra=False,variant='baseline'):
 queries=[]
 for i,f in enumerate(fixtures):
  queries.append({'event_id':'__fixture_'+str(i),'league':rows[0]['league'],'date':f['date'],'home':f['home'],'away':f['away'],'home_score':'0','away_score':'0','outcome':'no_contest','neutral':f.get('neutral','0'),'source':'verified schedule'})
 built,names=model_features(rows+queries,window,extra,variant)
 return {(r['date'],r['home'],r['away'],r['neutral']):(x,n,names) for r,x,n in built if r['event_id'].startswith('__fixture_')}

def prediction_context(db,root,league,allow_updated_history=False):
 rows=[r for r in load(db,league) if r['outcome'] in ('home','away')]
 experiments=db.execute('SELECT payload FROM experiments WHERE league=? ORDER BY created DESC',(league,)).fetchall()
 if not experiments: raise ValueError('Train and validate this league first')
 report=json.loads(experiments[0][0]); art=joblib.load(Path(root)/'models'/(report['id']+'.joblib'))
 if version(rows)!=art['digest']:
  training_ids=set(art.get('training_event_ids',[]))
  history=[r for r in rows if r['event_id'] in training_ids] if training_ids else [r for r in rows if r['date']<=art['last_date']]
  if not allow_updated_history or version(history)!=art['digest']: raise ValueError('Dataset changed; rerun validation')
 return {'league':league,'rows':rows,'report':report,'artifact':art,'input_digest':version(rows)}

def estimate(db,root,league,home,away,event_date,scenario=False,overrides=None,allow_updated_history=False,neutral=False,prepared_inputs=None,context=None):
 context=context or prediction_context(db,root,league,allow_updated_history)
 if context['league']!=league:raise ValueError('Prediction context belongs to another league')
 rows=context['rows'];report=context['report'];art=context['artifact']
 d=date.fromisoformat(event_date); latest=date.fromisoformat(rows[-1]['date'])
 if d<=latest: raise ValueError('Prediction date must follow all training results; historical backtests are in the experiment panel')
 if home==away or not all(any(r['home']==t or r['away']==t for r in rows) for t in (home,away)): raise ValueError('Choose two known opponents')
 if not scenario and (date.today()-latest).days>30: raise ValueError('Data are stale. Only explicitly hypothetical scenarios are available.')
 if not scenario and not 0<=(d-date.today()).days<=14: raise ValueError('Live prediction dates must be within the next 14 days')
 if not scenario and (d-latest).days>30: raise ValueError('Latest results too far from event date')
 if not scenario:
  for team in (home,away):
   recent=[r for r in rows if team in (r['home'],r['away']) and 0<(d-date.fromisoformat(r['date'])).days<=(1095 if league=='UFC' else 365)]
   if len(recent)<(3 if league=='UFC' else 5) or (d-date.fromisoformat(recent[-1]['date'])).days>{'UFC':730,'NBA':240,'WNBA':240,'NFL':240,'CFB':300,'MLB':180,'NHL':240}[league]: raise ValueError('Opponent has insufficient recent history; use a labeled scenario or withhold')
 future={'event_id':'__query__','league':league,'date':event_date,'home':home,'away':away,'home_score':'0','away_score':'0','outcome':'no_contest','neutral':'1' if neutral else '0','source':'manual unconfirmed matchup'}
 if overrides:
  if not scenario: raise ValueError('Overrides require scenario mode')
  permitted={'home_'+f for f in FEATURES[league]}|{'away_'+f for f in FEATURES[league]}|{'neutral'}
  if set(overrides)-permitted: raise ValueError('Unsupported scenario fields')
  if not art['extra'] and set(overrides)-{'neutral'}: raise ValueError('This result-only model cannot assess player, pitcher or advanced-stat overrides; those require a validated sport-feature model')
  if 'neutral' in overrides and str(overrides['neutral']) not in ('0','1'): raise ValueError('neutral must be 0 or 1')
  if str(overrides.get('neutral','0'))=='1' and art['model'] is not None and not art.get('neutral_variation',False): raise ValueError('Neutral-site sensitivity was not learned from this dataset; scenario withheld')
  if any(not math.isfinite(float(v)) for v in overrides.values()): raise ValueError('Scenario values must be finite')
  future.update({k:str(v) for k,v in overrides.items()})
 if art['extra'] and not all(s+'_'+f in future for f in FEATURES[league] for s in ('home','away')): raise ValueError('Selected model requires complete pregame sport-specific inputs; use scenario inputs or withhold')
 if prepared_inputs is not None and not overrides:
  x,n,names=prepared_inputs[(event_date,home,away,future['neutral'])]
 else:
  built,names=model_features(rows+[future],art['window'],art['extra'],art.get('variant','baseline')); _,x,n=built[-1]
 if n<(3 if league=='UFC' else 5): raise ValueError('Insufficient prior appearances for an opponent')
 X=np.array([x]); m=art['model']; p=float(elo(X)[0] if m is None else m.predict_proba(X)[0,1])
 factors=[{'factor':name,'difference':float(v)} for name,v in zip(names,x)]
 if m is not None and hasattr(m,'named_steps'):
  scaled=m.named_steps['standardscaler'].transform(X)[0]; contributions=scaled*m.named_steps['logisticregression'].coef_[0]
  for f,c in zip(factors,contributions): f['log_odds_contribution']=float(c)
 result={'league':league,'date':event_date,'home':home,'away':away,'home_probability':p,'away_probability':1-p,'mode':'hypothetical scenario' if scenario else 'limited forecast: unconfirmed manually entered fixture','model':art.get('selected',report['selected']),'experiment':report['id'],'dataset_sha256':art['digest'],'data_through':rows[-1]['date'],'weights_trained_through':art['last_date'],'input_dataset_sha256':context['input_digest'],'factors':factors,'rules':report['outcome_rules'],'availability':'Injuries, starters, lineups and schedule NOT confirmed','overrides':overrides or {},'explanation':'Logistic contributions explain the fitted log odds, not causation. Other models show input differences only; no invented importance scores.'}
 return result

def predict(db,root,league,home,away,event_date,scenario=False,overrides=None):
 result=estimate(db,root,league,home,away,event_date,scenario,overrides,allow_updated_history=True)
 with db: db.execute('INSERT INTO predictions(created,payload) VALUES(?,?)',(now(),json.dumps(result)))
 return result


def refit_frozen(db,root,league,force=False):
 """Compatibility entry point: automatic refreshes now use guarded loss review."""
 from .lifecycle import prepare, record
 rows=[r for r in load(db,league) if r['outcome'] in ('home','away')]
 stored=db.execute('SELECT payload FROM experiments WHERE league=? ORDER BY created LIMIT 1',(league,)).fetchone()
 if not stored:return 'No frozen specification; run the initial comparison explicitly'
 report=json.loads(stored[0]);path=Path(root)/'models'/(report['id']+'.joblib');state_root=Path(root)/'private-lifecycle'/league
 # Private history remains private. Score only saved pre-event forecasts, never scenarios.
 if not (state_root/'state.json').exists():prepare(state_root,rows,report,path)
 pending=[]
 for entry in db.execute('SELECT id,created,payload FROM predictions ORDER BY id'):
  p=json.loads(entry[2])
  if p.get('league')!=league or 'scenario' in p.get('mode','') or entry[1][:10]>=p.get('date',''):continue
  pending.append(dict(p,id=str(entry[0]),generated_at=entry[1]))
 record(state_root,pending)
 champion,summary=prepare(state_root,rows,report,path,outcomes=load(db,league))
 temporary=path.with_suffix('.tmp');joblib.dump(champion,temporary);temporary.replace(path)
 with db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('refit_'+league,json.dumps(summary)))
 return summary['status']
