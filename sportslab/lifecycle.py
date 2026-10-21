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
 from .research import review
 return review(rows,report)


def probabilities(art,rows,after):
 from .model import model_features
 built,_=model_features(rows,art['window'],art['extra'],art.get('variant','baseline'));ix=[i for i,v in enumerate(built) if v[0]['date']>after and v[2]>=(3 if rows[0]['league']=='UFC' else 5)];X=np.array([built[i][1] for i in ix])
 if not len(ix):return {},{}
 p=elo(X) if art['model'] is None else art['model'].predict_proba(X)[:,1]
 return {rows[i]['event_id']:float(v) for i,v in zip(ix,p)},{rows[i]['event_id']:rows[i] for i in ix}

def checkpoint_public_lineage(root,artifacts):
 """Record the exact verified training subset before backfilling earlier games."""
 from .data import connect
 from .pages import public_rows
 db=connect(root)
 for league_root in (Path(root)/'public-lifecycle').glob('*'):
  state_path=league_root/'state.json'
  if not state_path.exists():continue
  state=json.loads(state_path.read_text());reports=[league_root/'initial-report.json',*Path(artifacts).glob(league_root.name+'-*.json')]
  reports=[p for p in reports if p.exists() and not p.name.endswith('-heldout.json')]
  if not reports:continue
  report=json.loads(reports[0].read_text());rows=[r for r in public_rows(db,league_root.name) if r['outcome'] in ('home','away')]
  history=[r for r in rows if r['date']<=report['last_date']]
  if 'benchmark_event_ids' not in state and version(history)==report['dataset_sha256']:
   state['benchmark_event_ids']=[r['event_id'] for r in history];write_json(state_path,state)
  path=league_root/'champion.joblib'
  if path.exists():
   art=joblib.load(path);history=[r for r in rows if r['date']<=art['last_date']]
   if 'training_event_ids' not in art and version(history)==art['digest']:
    art['training_event_ids']=[r['event_id'] for r in history];joblib.dump(art,path)
 db.close()

def prepare(root,rows,report,original_path):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);state_path=root/'state.json';champion_path=root/'champion.joblib'
 state=json.loads(state_path.read_text()) if state_path.exists() else {'benchmark':report['dataset_sha256'],'ledger':{},'reviews':[],'consumed_losses':0}
 if state['benchmark']!=report['dataset_sha256']:raise ValueError('Champion benchmark lineage changed; explicit review required')
 if not champion_path.exists():joblib.dump(joblib.load(original_path),champion_path)
 champion=joblib.load(champion_path)
 # Detect source revisions or a partially restored cache; never silently train through them.
 training_ids=set(champion.get('training_event_ids',[]))
 historical=[r for r in rows if r['event_id'] in training_ids] if training_ids else [r for r in rows if r['date']<=champion['last_date']]
 if version(historical)!=champion['digest']:raise ValueError('Champion training history changed; forecasts withheld')
 if not training_ids:
  champion['training_event_ids']=[r['event_id'] for r in historical];joblib.dump(champion,champion_path)
 if 'benchmark_event_ids' not in state:
  benchmark_rows=[r for r in rows if r['date']<=report['last_date']]
  if version(benchmark_rows)==report['dataset_sha256']:state['benchmark_event_ids']=[r['event_id'] for r in benchmark_rows]
 backtest_review=None
 if len(rows)>=700 and 'final_test_start' in report:
  from .research import saved_review
  backtest_review=saved_review(root,rows,report)
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
 summary={'status':status,'policy':POLICY,'checked':now(),'champion':champion.get('selected',report['selected']),'weights_trained_through':champion['last_date'],'live_record':{'wins':wins,'losses':losses,'pending':sum(not e.get('settled') for e in state['ledger'].values())},'trial':state.get('trial'),'confirmation':state.get('confirmation'),'last_decision':state['reviews'][-1] if state['reviews'] else None,'research':state.get('research'),'backtest_review':backtest_review}
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
