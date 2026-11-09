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

def confirmation_after(trial):
 # Date-grouped inference cannot establish ordering within the lock date.
 # Late imports of already-played games must not become future confirmation.
 return max(trial['after'],trial.get('created',trial['after'])[:10])

def candidate(rows,report,champion=None):
 from .research import review
 return review(rows,report,champion)


def probabilities(art,rows,after):
 from .model import model_features
 rows=[r for r in rows if r['date']>=art.get('history_from','0001-01-01')]
 variant=art.get('variant','baseline');built,names=model_features(rows,art['window'],art['extra'],variant)
 if variant not in ('no_rest','rest_guard') and not variant.startswith('context_'):
  from .rest import adjusted_features
  built,_=adjusted_features(built,names,'recovery_only')
 ix=[i for i,v in enumerate(built) if v[0]['date']>after and v[2]>=(3 if rows[0]['league']=='UFC' else 5)];X=np.array([built[i][1] for i in ix])
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

def prepare(root,rows,report,original_path,outcomes=None):
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
 backtest_review=None;recent_review=None;adaptive_review=None
 if len(rows)>=700 and 'final_test_start' in report:
  from .research import saved_review
  backtest_review=saved_review(root,rows,report,champion)
  from .adaptive import saved_review as saved_adaptive_review
  try:adaptive_review=saved_adaptive_review(root,rows,report,champion,backtest_review)
  except ValueError as error:adaptive_review={'status':'research pending','error':str(error),'new_method_selected':False}
  if report['league']=='NBA':
   from .nba import saved_recent_review
   recent_review=saved_recent_review(root,rows,backtest_review)
   from .adaptive import saved_recent_review as adaptive_recent_review
   if adaptive_review is not None:
    try:adaptive_review['recent_data_research']=adaptive_recent_review(root,rows,recent_review)
    except ValueError as error:adaptive_review['recent_data_research']={'status':'research pending','error':str(error),'new_method_selected':False}
    from .nba_context import saved_review as nba_context_review
    try:adaptive_review['nba_focus_research']=nba_context_review(root,rows,recent_review)
    except ValueError as error:adaptive_review['nba_focus_research']={'status':'research pending','error':str(error),'new_method_selected':False}
 final_rows=outcomes if outcomes is not None else rows
 from .grading import ResultIndex
 index=ResultIndex(final_rows)
 all_entries=list(state['ledger'].values())+[e for ledger in state.get('policy_ledgers',{}).values() for e in ledger.values()]
 for entry in all_entries:
  result=index.find(entry)
  if result:
   excluded=bool(entry.get('grading_excluded'))
   if result.get('start_time') and entry.get('generated_at'):
    from .pages import parse_time
    excluded=parse_time(entry['generated_at'])>=parse_time(result['start_time'])
   entry.update(settled=True,outcome=None if excluded else result['outcome'],final_outcome=result['outcome'],grading_excluded=excluded,home_score=result.get('home_score'),away_score=result.get('away_score'))
   entry['correct']=((entry['home_probability']>=.5)==(result['outcome']=='home')) if not excluded and result['outcome'] in ('home','away') else None
 from .rest import VERSION as rest_version
 feedback_policy=rest_version if rest_version in state.get('policy_ledgers',{}) else 'legacy'
 feedback=state.get('policy_ledgers',{}).get(rest_version,state['ledger'])
 if state.get('feedback_policy','legacy')!=feedback_policy:
  state['consumed_losses']=0;state['adaptive_consumed_results']=0
 state['feedback_policy']=feedback_policy
 losses=sum(e.get('correct') is False for e in feedback.values());wins=sum(e.get('correct') is True for e in feedback.values())
 state['consumed_losses']=min(state['consumed_losses'],losses)
 state['adaptive_consumed_results']=min(state.get('adaptive_consumed_results',0),wins+losses)
 trial=state.get('trial')
 if trial and trial.get('prediction_policy')!=rest_version:
  state.setdefault('policy_changes',[]).append({'at':now(),'previous_trial_after':trial['after'],'prediction_policy':rest_version})
  trial.update(after=rows[-1]['date'],prediction_policy=rest_version);state['confirmation']=None
 status='Champion retained; waiting for settled forecast losses before opening a review.'
 if trial:
  challenger=joblib.load(root/'challenger.joblib');old,rr=probabilities(champion,rows,confirmation_after(trial));new,_=probabilities(challenger,rows,confirmation_after(trial));ids=sorted(set(old)&set(new),key=lambda k:(rr[k]['date'],k))
  decision=gate(np.array([int(rr[k]['outcome']=='home') for k in ids]),np.array([old[k] for k in ids]),np.array([new[k] for k in ids]),[rr[k]['date'] for k in ids]);state['confirmation']=decision
  status=f"Challenger locked; {decision['n']}/{POLICY['minimum_results']} new results across {decision['weeks']}/{POLICY['minimum_weeks']} weeks."
  if decision['status']!='collecting evidence':
   state['reviews'].append(dict(decision,reviewed=now(),trial_after=trial['after']));state['trial']=None;state['consumed_losses']=losses
   if decision['promote']:
    joblib.dump(champion,root/'previous-champion.joblib');temporary=root/'champion.tmp';joblib.dump(challenger,temporary);temporary.replace(champion_path);champion=challenger
   status='Challenger promoted after passing all checks.' if decision['promote'] else 'Champion retained: challenger did not pass every improvement check.'
 elif losses>state['consumed_losses']:
  if recent_review and (recent_review.get('confirmation') or {}).get('passed'):
   from .nba import refit_recent_candidate
   challenger=refit_recent_candidate(root,rows);research=recent_review
  else:challenger,research=candidate(rows,report,champion)
  state['research']=research
  if challenger is not None:
   state['consumed_losses']=losses
   joblib.dump(challenger,root/'challenger.joblib');state['trial']={'after':rows[-1]['date'],'created':now(),'selected':research['selected'],'prediction_policy':rest_version};status='Loss review opened; challenger locked. Waiting for new results to backtest both models fairly.'
  else:status='Challenger fitting pending; hourly checks will retry when enough calibration data are available.'
 champion,feedback_status=nba_feedback_trial(root,state,rows,champion,champion_path,backtest_review,losses,recent_review)
 if feedback_status:status=feedback_status
 from .adaptive import trial as adaptive_trial
 champion,adaptive_status=adaptive_trial(root,state,rows,report,champion,champion_path,adaptive_review,losses,observations=wins+losses)
 if adaptive_status:status=adaptive_status
 summary={'status':status,'prediction_policy':rest_version,'feedback_policy':feedback_policy,'policy':POLICY,'checked':now(),'champion':champion.get('selected',report['selected']),'weights_trained_through':champion['last_date'],'outcome_learning':outcome_learning(feedback),'live_record':{'wins':wins,'losses':losses,'pending':sum(not e.get('settled') for e in feedback.values())},'trial':state.get('trial'),'confirmation':state.get('confirmation'),'last_decision':state['reviews'][-1] if state['reviews'] else None,'research':state.get('research'),'backtest_review':backtest_review,'feedback_report':feedback_report(feedback),'nba_feedback_trial':state.get('nba_feedback_trial'),'nba_recent_review':recent_review,'adaptive_review':adaptive_review,'adaptive_trial':state.get('adaptive_trial')}
 write_json(state_path,state)
 return champion,summary

def record(root,predictions):
 path=Path(root)/'state.json'
 if not path.exists():return
 state=json.loads(path.read_text())
 for p in predictions:
  # First published pre-event forecast is immutable; later refreshes cannot replace misses.
  entry={k:p[k] for k in ('id','date','home','away','home_probability','generated_at','model','dataset_sha256','event_start_utc','prediction_policy','injury_context','availability','interpretation_summary') if k in p}
  state['ledger'].setdefault(p['id'],dict(entry))
  if p.get('prediction_policy'):
   state.setdefault('policy_ledgers',{}).setdefault(p['prediction_policy'],{}).setdefault(p['id'],dict(entry))
 from .rest import VERSION
 feedback=state.get('policy_ledgers',{}).get(VERSION,state['ledger'])
 feedback_policy=VERSION if VERSION in state.get('policy_ledgers',{}) else 'legacy'
 if state.get('feedback_policy','legacy')!=feedback_policy:
  state['consumed_losses']=0;state['adaptive_consumed_results']=0
 state['feedback_policy']=feedback_policy
 write_json(path,state)
 return {'wins':sum(e.get('correct') is True for e in feedback.values()),'losses':sum(e.get('correct') is False for e in feedback.values()),'pending':sum(not e.get('settled') for e in feedback.values())}


def feedback_report(entries):
 """Score immutable pregame picks; never rebuild forecasts from known results."""
 from .diagnostics import analyze
 settled=[e for e in entries.values() if e.get('settled') and e.get('outcome') in ('home','away')]
 if not settled:return {'n':0,'metrics':None,'accuracy_95':None,'confidence_bands':[],'largest_misses':[]}
 y=np.array([int(e['outcome']=='home') for e in settled]);p=np.array([e['home_probability'] for e in settled]);metrics=scores(y,p);n=len(y);rate=metrics['accuracy'];z=1.96;den=1+z*z/n;center=(rate+z*z/(2*n))/den;radius=z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/den
 bands=[];confidence=np.maximum(p,1-p);correct=(p>=.5)==y
 for lo,hi in ((.5,.6),(.6,.7),(.7,.8),(.8,1.000001)):
  ix=(confidence>=lo)&(confidence<hi)
  if ix.any():bands.append({'from':lo,'to':min(hi,1.),'n':int(ix.sum()),'mean_confidence':float(confidence[ix].mean()),'accuracy':float(correct[ix].mean())})
 misses=[]
 for e in settled:
  if (e['home_probability']>=.5)==(e['outcome']=='home'):continue
  misses.append({k:e[k] for k in ('id','date','home','away','home_probability','generated_at','outcome','model') if k in e})
 misses.sort(key=lambda e:(max(e['home_probability'],1-e['home_probability']),e['date']),reverse=True)
 return {'n':n,'metrics':metrics,'accuracy_95':[max(0.,float(center-radius)),min(1.,float(center+radius))],'confidence_bands':bands,'largest_misses':misses[:8],'diagnostics':analyze(settled),'note':'Original saved pregame forecasts under the current prediction policy. Small samples are noisy; the Wilson accuracy interval is descriptive and assumes independent picks. Wins and losses both inform training; no result rewrites a saved pick.'}


def nba_feedback_trial(root,state,rows,champion,champion_path,review,losses,recent_review=None):
 """Lock an additional NBA candidate without replacing an ongoing trial."""
 import hashlib
 if rows[0]['league']!='NBA' or not review:return champion,None
 source=Path(root)/'research-challenger.joblib';trial=state.get('nba_feedback_trial')
 if recent_review and (recent_review.get('confirmation') or {}).get('passed'):
  review=recent_review;source=Path(root)/'nba-recent-challenger.joblib'
 if not trial and losses and source.exists():
  if review.get('selected') and (state.get('trial') or {}).get('selected')==review['selected']:return champion,None
  from .research import NBA_VERSION
  from .nba import RECENT_VERSION
  if review['version'] not in (NBA_VERSION,RECENT_VERSION):return champion,None
  if review['version']==RECENT_VERSION:
   from .nba import refit_recent_candidate
   challenger=refit_recent_candidate(root,rows)
  else:challenger=joblib.load(source)
  joblib.dump(challenger,Path(root)/'nba-feedback-challenger.joblib')
  joblib.dump(champion,Path(root)/'nba-feedback-reference.joblib')
  trial={'version':review['version'],'after':rows[-1]['date'],'created':now(),'selected':challenger['selected'],'weights_through':challenger['last_date'],'champion_sha256':hashlib.sha256(champion_path.read_bytes()).hexdigest(),'status':'collecting evidence'}
  state['nba_feedback_trial']=trial
 if not trial or trial['status']!='collecting evidence':return champion,None
 if hashlib.sha256(champion_path.read_bytes()).hexdigest()!=trial['champion_sha256']:
  trial['status']='superseded by champion change';return champion,None
 challenger=joblib.load(Path(root)/'nba-feedback-challenger.joblib');reference=joblib.load(Path(root)/'nba-feedback-reference.joblib');old,rr=probabilities(reference,rows,confirmation_after(trial));new,_=probabilities(challenger,rows,confirmation_after(trial));ids=sorted(set(old)&set(new),key=lambda k:(rr[k]['date'],k))
 decision=gate(np.array([int(rr[k]['outcome']=='home') for k in ids]),np.array([old[k] for k in ids]),np.array([new[k] for k in ids]),[rr[k]['date'] for k in ids]);trial['confirmation']=decision
 if decision['status']=='collecting evidence':return champion,None
 trial['status']=decision['status'];state['reviews'].append(dict(decision,reviewed=now(),trial_after=trial['after'],source='NBA feedback candidate'))
 if not decision['promote']:return champion,None
 joblib.dump(champion,Path(root)/'previous-champion.joblib');temporary=champion_path.with_suffix('.tmp');joblib.dump(challenger,temporary);temporary.replace(champion_path)
 if state.get('trial'):state.setdefault('superseded_trials',[]).append({'trial':state['trial'],'confirmation':state.get('confirmation'),'at':now()})
 state['trial']=None;state['confirmation']=None;state['consumed_losses']=losses
 return challenger,'NBA feedback challenger promoted after independent improvement checks.'


def outcome_learning(entries):
 """Audit actual frozen forecasts; both upset directions contribute to learning."""
 import math
 observations=[]
 for entry in entries.values():
  if not entry.get('settled') or entry.get('grading_excluded') or entry.get('outcome') not in ('home','away'):continue
  p=entry.get('home_probability')
  if not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1:continue
  y=int(entry['outcome']=='home');actual=p if y else 1-p;error=y-p
  observations.append({'id':entry['id'],'date':entry['date'],'home':entry['home'],'away':entry['away'],'winner':entry['home'] if y else entry['away'],'winner_probability':actual,'prediction_error':error,'surprise':abs(error),'log_loss':-math.log(max(1e-12,actual)),'correct':(p>=.5)==bool(y)})
 observations.sort(key=lambda e:(e['surprise'],e['date']),reverse=True)
 return {'settled_results':len(observations),'correct':sum(e['correct'] for e in observations),'incorrect':sum(not e['correct'] for e in observations),'mean_surprise':sum(e['surprise'] for e in observations)/len(observations) if observations else None,'largest_surprises':observations[:12],'update_policy':'Every newly settled decisive result can trigger an eligible adaptive challenger refit. Both wins and losses update causal team/fighter feedback. Larger unexpected outcomes generate larger residuals; live promotion requires independent accuracy, log-loss and Brier checks.'}
