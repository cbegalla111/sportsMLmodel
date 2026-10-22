"""Synthetic schedule context only; no example outcomes enter published data."""
from datetime import date,timedelta
import copy
import numpy as np
import pytest
from sportslab.rest import comparison,adjusted_features,POLICIES
from sportslab.model import features
from test_model import synthetic_rows


def last(day,gap):return (date.fromisoformat(day)-timedelta(days=gap)).isoformat()


def test_offseason_or_missing_history_never_earns_recovery_credit():
 day='2026-10-22'
 for league,p in POLICIES.items():
  c=comparison(league,day,last(day,p['typical_days']),last(day,p['inactive_after_days']+1))
  assert not c['reliable_comparison'] and c['recovery_difference']==0
  assert comparison(league,day,None,last(day,p['typical_days']))['recovery_difference']==0
 c=comparison('NBA',day,'2026-10-20','2026-05-26')
 assert c['home_gap_days']==2 and c['away_gap_days']==149 and c['recovery_difference']==0


def test_caps_and_normal_intervals_are_specific_to_each_sport():
 day='2026-10-22'
 assert comparison('NBA',day,last(day,2),last(day,10))['recovery_difference']==-1
 assert comparison('NFL',day,last(day,7),last(day,10))['recovery_difference']==-3
 assert comparison('MLB',day,last(day,1),last(day,7))['recovery_difference']==-2
 assert comparison('UFC',day,last(day,90),last(day,180))['recovery_difference']==-1
 assert comparison('UFC',day,last(day,90),last(day,360))['recovery_difference']==-1


@pytest.mark.parametrize('variant',['context_baseline','context_form','context_ratings','rest_guard','no_rest'])
def test_context_features_are_causal_and_queries_do_not_update_history(variant):
 from sportslab.research import build
 rows=synthetic_rows(160);original,names=build(rows,20,variant);changed=copy.deepcopy(rows);cut=rows[80]['date']
 for r in changed:
  if r['date']>=cut:r.update(home_score='500',away_score='0',outcome='home')
 altered,_=build(changed,20,variant)
 assert all(a[1]==b[1] for a,b in zip(original,altered) if a[0]['date']<=cut)
 query=dict(rows[-1],event_id='query',date='2010-02-10',outcome='no_contest')
 duplicate=dict(query,event_id='duplicate')
 q,_=build(rows+[query,duplicate],20,variant)
 assert q[-1][1]==q[-2][1]
 assert np.isfinite(np.array([r[1] for r in q])).all()


def test_guard_backtest_uses_original_training_weights_and_corrected_inputs():
 from sportslab.research import fit,predict
 from sportslab.model import estimator
 rows=synthetic_rows(800);base,_=features(rows);guard,_=adjusted_features(base,['elo_difference','home_advantage','win_rate_difference','scoring_margin_difference','rest_difference'],'guard')
 X=np.array([r[1] for r in base]);G=np.array([r[1] for r in guard]);y=np.array([r['outcome']=='home' for r in rows],dtype=int);ds=[r['date'] for r in rows]
 m=fit({'kind':'logistic','variant':'rest_guard','c':.1,'guard_legacy':True},G[:600],y[:600],ds[:600],'NBA')
 legacy=estimator('logistic');legacy.fit(X[:600],y[:600])
 assert np.allclose(m.model.named_steps['logisticregression'].coef_,legacy.named_steps['logisticregression'].coef_)
 assert np.allclose(predict(m,G[600:]),legacy.predict_proba(G[600:,:-1])[:,1])


def test_live_inference_and_confirmation_use_identical_rest_policy(tmp_path):
 import json,joblib
 from sportslab.data import connect,ingest,version,load
 from sportslab.model import estimate,estimator
 from sportslab.lifecycle import probabilities
 rows=synthetic_rows(120);db=connect(tmp_path);ingest(db,rows);rows=load(db,'NBA');built,names=features(rows);X=np.array([r[1] for r in built]);y=np.array([r['outcome']=='home' for r in rows],dtype=int)
 m=estimator('logistic');m.fit(X,y)
 art={'model':m,'window':20,'extra':False,'names':names,'digest':version(rows),'training_event_ids':[r['event_id'] for r in rows],'last_date':rows[-1]['date'],'league':'NBA'}
 (tmp_path/'models').mkdir();joblib.dump(art,tmp_path/'models'/'test.joblib')
 report={'id':'test','selected':'logistic_w20','outcome_rules':'Synthetic test only'}
 with db:db.execute('INSERT INTO experiments VALUES(?,?,?,?)',('test','NBA','2020-01-01',json.dumps(report)))
 p=estimate(db,tmp_path,'NBA','T0','T1','2010-07-01',scenario=True)
 query=dict(rows[-1],event_id='target',date='2010-07-01',home='T0',away='T1',outcome='home')
 predicted,_=probabilities(art,rows+[query],rows[-1]['date'])
 assert predicted['target']==pytest.approx(p['home_probability'])
 assert p['rest_context']['recovery_difference']==0
 assert next(f for f in p['factors'] if f['factor']=='contextual_recovery_difference')['difference']==0
