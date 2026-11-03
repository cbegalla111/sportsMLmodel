"""Synthetic outcomes only; research never publishes these fixtures."""
import copy
import json
from pathlib import Path
import joblib
import numpy as np
import pytest
from test_model import synthetic_rows
from sportslab.adaptive import feedback_features,definitions,saved_review,trial
from sportslab.research import build,fit,label

@pytest.mark.parametrize('league',['NBA','MLB','UFC'])
def test_future_and_same_day_outcomes_cannot_change_inputs(league):
 rows=synthetic_rows(100)
 for r in rows:r['league']=league
 original,_=feedback_features(rows);changed=copy.deepcopy(rows);day=rows[48]['date']
 for r in changed:
  if r['date']>=day:r.update(home_score='500',away_score='0',outcome='home')
 modified,_=feedback_features(changed)
 for a,b in zip(original,modified):
  if a[0]['date']<=day:assert a[1]==b[1]
 assert any(a[1][-7:]!=b[1][-7:] for a,b in zip(original,modified) if a[0]['date']>day)

def test_adaptive_same_date_batch_order_and_no_fake_ufc_margins():
 rows=synthetic_rows(100);a,_=feedback_features(rows);b,_=feedback_features(list(reversed(rows)))
 assert {r['event_id']:x[-7:] for r,x,_ in a}=={r['event_id']:x[-7:] for r,x,_ in b}
 for r in rows:r['league']='UFC'
 a,_=feedback_features(rows);changed=[dict(r,home_score='999',away_score='-999') for r in rows];b,_=feedback_features(changed)
 assert [x[-7:] for _,x,_ in a]==[x[-7:] for _,x,_ in b]
 assert all(x[-1]==0 for _,x,_ in a)

def test_catalog_unique_and_blend_keeps_bayesian_and_rest_columns(tmp_path):
 specs=definitions();assert len(specs)==21 and len({label(s) for s in specs})==21
 rows=synthetic_rows(800);built,names=build(rows,20,'context_feedback');X=np.array([x for _,x,_ in built]);y=np.array([r['outcome']=='home' for r,_,_ in built]);days=[r['date'] for r,_,_ in built]
 for spec in (specs[0],specs[-1],specs[-6]):
  m=fit(spec,X,y,days,'NBA');p=m.predict_proba(X[-10:]);assert np.isfinite(p).all() and np.allclose(p.sum(axis=1),1)
  path=tmp_path/'model.joblib';joblib.dump(m,path);assert np.allclose(joblib.load(path).predict_proba(X[-10:]),p)

def test_final_period_changes_do_not_reselect_research(tmp_path,monkeypatch):
 rows=synthetic_rows(800);report={'league':'NBA','selected':'elo_w20','final_test_start':rows[600]['date'],'last_date':rows[-1]['date']};champion={'selected':'elo_w20','research_spec':{'kind':'elo','variant':'baseline','window':20}}
 monkeypatch.setattr('sportslab.adaptive.definitions',lambda:[{'kind':'logistic','variant':'context_feedback','window':20,'c':.03,'decay':False}])
 r=saved_review(tmp_path/'new',rows,report,champion,None)
 changed=copy.deepcopy(rows)
 for row in changed:
  if row['date']>=report['final_test_start']:row.update(home_score='999',away_score='0',outcome='home')
 again=saved_review(tmp_path/'new',changed,report,champion,None)
 assert r==again
 assert all(f['train_end']<f['validation_start']<=f['validation_end']<report['final_test_start'] for c in r['candidates'] for f in c['folds'])

def test_existing_trial_is_not_replaced_and_reference_changes_invalidate(tmp_path):
 path=tmp_path/'champion.joblib';joblib.dump({'selected':'old'},path)
 state={'adaptive_trial':{'status':'collecting evidence','reference_sha256':'different'},'reviews':[]}
 champion,status=trial(tmp_path,state,synthetic_rows(120),{}, {'selected':'old'},path,{'new_method_selected':True},1)
 assert state['adaptive_trial']['status']=='superseded by champion change' and status is None
 assert champion['selected']=='old' and not (tmp_path/'adaptive-trial-model.joblib').exists()

def test_loss_opens_frozen_trial_and_only_independent_gate_changes_champion(tmp_path,monkeypatch):
 from datetime import date,timedelta
 import hashlib
 path=tmp_path/'champion.joblib';champion={'selected':'old','variant':'baseline'};joblib.dump(champion,path);before=path.read_bytes()
 spec={'kind':'logistic','variant':'context_feedback','window':20,'c':.3};challenger={'selected':'adaptive','variant':'context_feedback','research_spec':spec}
 research={'new_method_selected':True,'fingerprint':'fixed-development','best':{'specification':spec}}
 state={'reviews':[],'ledger':{'unchanged':{'home_probability':.7}},'trial':{'selected':'original trial'},'confirmation':None,'consumed_losses':0}
 monkeypatch.setattr('sportslab.research.review',lambda *a:(challenger,{}))
 current,status=trial(tmp_path,state,synthetic_rows(120),{},champion,path,research,0)
 assert not state.get('adaptive_trial')
 current,status=trial(tmp_path,state,synthetic_rows(120),{},champion,path,research,1)
 assert state['adaptive_trial']['status']=='collecting evidence' and path.read_bytes()==before
 locked=(tmp_path/'adaptive-trial-model.joblib').read_bytes()
 monkeypatch.setattr('sportslab.lifecycle.probabilities',lambda *a:({},{}))
 current,status=trial(tmp_path,state,synthetic_rows(120),{},champion,path,research,2)
 assert (tmp_path/'adaptive-trial-model.joblib').read_bytes()==locked and state['trial']['selected']=='original trial'
 matches={str(i):{'date':(date(2020,1,1)+timedelta(days=i)).isoformat(),'outcome':'home' if i%2 else 'away'} for i in range(200)}
 def prospective(art,*args):
  confidence=.8 if art['selected']=='adaptive' else .55
  return {k:confidence if r['outcome']=='home' else 1-confidence for k,r in matches.items()},matches
 monkeypatch.setattr('sportslab.lifecycle.probabilities',prospective)
 current,status=trial(tmp_path,state,synthetic_rows(120),{},champion,path,research,2)
 assert current['selected']=='adaptive' and state['adaptive_trial']['confirmation']['promote']
 assert state['trial'] is None and state['superseded_trials'][0]['trial']['selected']=='original trial'
 assert state['ledger']=={'unchanged':{'home_probability':.7}}
 assert joblib.load(path)['selected']=='adaptive'

def test_trial_cutoff_excludes_backfilled_prelock_dates():
 from sportslab.lifecycle import confirmation_after,probabilities
 from sportslab.data import version
 rows=synthetic_rows(160)
 state={'after':rows[100]['date'],'created':rows[-1]['date']+'T12:00:00+00:00'}
 assert confirmation_after(state)==rows[-1]['date']
 artifact={'model':None,'window':20,'extra':False,'variant':'baseline','league':'NBA','digest':version(rows),'last_date':rows[100]['date']}
 assert probabilities(artifact,rows,confirmation_after(state))==({},{})
 assert confirmation_after({'after':'2020-01-01'})=='2020-01-01'

def test_locked_adaptive_challenger_runs_through_production_inference(tmp_path):
 from sportslab.lifecycle import probabilities
 rows=synthetic_rows(800);spec={'kind':'logistic','window':20,'variant':'context_feedback','c':.03,'decay':False}
 built,names=build(rows,20,spec['variant']);X=np.array([x for _,x,_ in built]);y=np.array([r['outcome']=='home' for r,_,_ in built]);days=[r['date'] for r,_,_ in built]
 m=fit(spec,X,y,days,'NBA');artifact={'model':m,'window':20,'extra':False,'variant':spec['variant'],'league':'NBA','research_spec':spec}
 path=tmp_path/'challenger.joblib';joblib.dump(artifact,path);restored=joblib.load(path)
 p,results=probabilities(restored,rows,rows[700]['date'])
 assert p and len(p)==len(results)
 assert all(0<=value<=1 for value in p.values())
 assert all(r['date']>rows[700]['date'] for r in results.values())

def test_failed_nba_historical_confirmation_cannot_open_a_trial(tmp_path):
 path=tmp_path/'champion.joblib';champion={'selected':'old'};joblib.dump(champion,path);before=path.read_bytes();state={'reviews':[]}
 research={'new_method_selected':False,'nba_focus_research':{'new_method_selected':True,'confirmation':{'passed':False}}}
 result,status=trial(tmp_path,state,synthetic_rows(120),{},champion,path,research,5)
 assert result==champion and status is None and not state.get('adaptive_trial')
 assert path.read_bytes()==before and not (tmp_path/'adaptive-trial-model.joblib').exists()
