"""Prospective loss review. Public-only ledger; original final tests stay sealed."""
import json
from datetime import date
from pathlib import Path
import joblib
import numpy as np
from .data import now, version
from .model import features, estimator, elo, scores

POLICY={'minimum_results':100,'minimum_weeks':8,'minimum_log_loss_gain':.002,'bootstrap_samples':1000,'description':'After a settled forecast loss, lock a challenger before collecting a new confirmation sample. Promote only for lower log loss, non-worse Brier and accuracy, and a paired weekly bootstrap showing improvement. No changes after a single upset.'}

def write_json(path,value):
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,allow_nan=False));temporary.replace(path)

def gate(y,incumbent,challenger,days):
 weeks=np.array([date.fromisoformat(d).strftime('%G-%V') for d in days]);unique=np.unique(weeks)
 if len(y)<POLICY['minimum_results'] or len(unique)<POLICY['minimum_weeks']:
  return {'status':'collecting evidence','n':len(y),'weeks':len(unique),'promote':False}
 old=scores(y,incumbent);new=scores(y,challenger)
 cp=np.clip(challenger,1e-6,1-1e-6);ip=np.clip(incumbent,1e-6,1-1e-6)
 delta=-(y*np.log(cp)+(1-y)*np.log(1-cp))+(y*np.log(ip)+(1-y)*np.log(1-ip))
 sums=np.array([delta[weeks==w].sum() for w in unique]);counts=np.array([(weeks==w).sum() for w in unique]);rng=np.random.default_rng(42)
 draws=rng.integers(0,len(unique),size=(POLICY['bootstrap_samples'],len(unique)))
 interval=np.quantile(sums[draws].sum(axis=1)/counts[draws].sum(axis=1),[.025,.975]).tolist()
 promote=(old['log_loss']-new['log_loss']>=POLICY['minimum_log_loss_gain'] and new['brier']<=old['brier'] and new['accuracy']>=old['accuracy'] and interval[1]<0)
 return {'status':'promoted' if promote else 'retained champion','n':len(y),'weeks':len(unique),'promote':bool(promote),'champion':old,'challenger':new,'paired_log_loss_delta_95':interval,'from':days[0],'through':days[-1]}

def candidate(rows,report):
 """Choose on expanding development folds, excluding the archived final-test dates."""
 ds=np.array([r['date'] for r in rows]);days=sorted(set(ds));cut=report.get('final_test_start',days[int(len(days)*.8)])
 allowed=(ds<cut)|(ds>report['last_date']);candidates=[];cache={}
 for kind,window in [('logistic',10),('logistic',20),('logistic_strong',20),('logistic_weak',20),('boost',20),('logistic',40),('boost',40)]:
  built,names=features(rows,window);X=np.array([v[1] for v in built]);y=np.array([v[0]['outcome']=='home' for v in built],dtype=int);warm=np.array([v[2]>=5 for v in built]);folds=[]
  for left,right in ((.4,.6),(.6,.8),(.8,1.0)):
   start=days[int(len(days)*left)];end=days[min(len(days)-1,int(len(days)*right))];tr=(ds<start)&warm;va=(ds>=start)&(ds<end)&warm&allowed
   if va.sum()<20 or len(set(y[tr]))<2:continue
   m=estimator(kind);m.fit(X[tr],y[tr]);p=m.predict_proba(X[va])[:,1];folds.append(dict(scores(y[va],p),train_end=str(max(ds[tr])),validation_start=str(min(ds[va])),validation_end=str(max(ds[va]))))
  if not folds:continue
  name=f'{kind}_w{window}';candidates.append({'name':name,'folds':folds,'mean_log_loss':float(np.mean([f['log_loss'] for f in folds]))});cache[name]=(kind,window,X,y,warm,names)
 if not candidates:return None,{'status':'Not enough untouched development data for a challenger'}
 selected=min(candidates,key=lambda c:c['mean_log_loss'])['name'];kind,window,X,y,warm,names=cache[selected];model=estimator(kind);model.fit(X[warm],y[warm])
 art={'model':model,'window':window,'extra':False,'names':names,'digest':version(rows),'last_date':rows[-1]['date'],'league':report['league'],'neutral_variation':len(np.unique(X[warm,1]))>1,'selected':selected,'refitted':now()}
 return art,{'selected':selected,'candidates':candidates,'note':'Development comparison only; promotion requires a separate prospective confirmation window.'}

def probabilities(art,rows,after):
 built,_=features(rows,art['window'],art['extra']);ix=[i for i,v in enumerate(built) if v[0]['date']>after and v[2]>=5];X=np.array([built[i][1] for i in ix])
 if not len(ix):return {},{}
 p=elo(X) if art['model'] is None else art['model'].predict_proba(X)[:,1]
 return {rows[i]['event_id']:float(v) for i,v in zip(ix,p)},{rows[i]['event_id']:rows[i] for i in ix}

def prepare(root,rows,report,original_path):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);state_path=root/'state.json';champion_path=root/'champion.joblib'
 state=json.loads(state_path.read_text()) if state_path.exists() else {'benchmark':report['dataset_sha256'],'ledger':{},'reviews':[],'consumed_losses':0}
 if state['benchmark']!=report['dataset_sha256']:raise ValueError('Champion benchmark lineage changed; explicit review required')
 if not champion_path.exists():joblib.dump(joblib.load(original_path),champion_path)
 champion=joblib.load(champion_path)
 # Detect source revisions or a partially restored cache; never silently train through them.
 historical=[r for r in rows if r['date']<=champion['last_date']]
 if version(historical)!=champion['digest']:raise ValueError('Champion training history changed; forecasts withheld')
 by_match={(r['date'],r['home'],r['away']):r for r in rows}
 for entry in state['ledger'].values():
  if entry.get('settled'):continue
  result=by_match.get((entry['date'],entry['home'],entry['away']))
  if result:
   entry.update(settled=True,outcome=result['outcome'])
   if result['outcome'] in ('home','away'):entry['correct']=(entry['home_probability']>=.5)==(result['outcome']=='home')
 losses=sum(e.get('correct') is False for e in state['ledger'].values());wins=sum(e.get('correct') is True for e in state['ledger'].values())
 trial=state.get('trial');status='Champion retained; waiting for settled forecast losses before opening a review.'
 if trial:
  challenger=joblib.load(root/'challenger.joblib');old,rr=probabilities(champion,rows,trial['after']);new,_=probabilities(challenger,rows,trial['after']);ids=sorted(set(old)&set(new),key=lambda k:(rr[k]['date'],k))
  decision=gate(np.array([int(rr[k]['outcome']=='home') for k in ids]),np.array([old[k] for k in ids]),np.array([new[k] for k in ids]),[rr[k]['date'] for k in ids]);state['confirmation']=decision
  status=f"Challenger locked; {decision['n']}/{POLICY['minimum_results']} new results across {decision['weeks']}/{POLICY['minimum_weeks']} weeks."
  if decision['status']!='collecting evidence':
   state['reviews'].append(dict(decision,reviewed=now(),trial_after=trial['after']));state['trial']=None;state['consumed_losses']=losses
   if decision['promote']:
    joblib.dump(champion,root/'previous-champion.joblib');temporary=root/'champion.tmp';joblib.dump(challenger,temporary);temporary.replace(champion_path);champion=challenger
   status='Challenger promoted after passing all checks.' if decision['promote'] else 'Champion retained: challenger did not pass every improvement check.'
 elif losses>state['consumed_losses']:
  challenger,research=candidate(rows,report);state['research']=research;state['consumed_losses']=losses
  if challenger:
   joblib.dump(challenger,root/'challenger.joblib');state['trial']={'after':rows[-1]['date'],'created':now(),'selected':research['selected']};status='Loss review opened; challenger locked. Waiting for new results to backtest both models fairly.'
 summary={'status':status,'policy':POLICY,'checked':now(),'champion':champion.get('selected',report['selected']),'weights_trained_through':champion['last_date'],'live_record':{'wins':wins,'losses':losses,'pending':sum(not e.get('settled') for e in state['ledger'].values())},'trial':state.get('trial'),'confirmation':state.get('confirmation'),'last_decision':state['reviews'][-1] if state['reviews'] else None,'research':state.get('research')}
 write_json(state_path,state)
 return champion,summary

def record(root,predictions):
 path=Path(root)/'state.json'
 if not path.exists():return
 state=json.loads(path.read_text())
 for p in predictions:
  # First published pre-event forecast is immutable; later refreshes cannot replace misses.
  state['ledger'].setdefault(p['id'],{k:p[k] for k in ('id','date','home','away','home_probability','generated_at','model','dataset_sha256')})
 write_json(path,state)
