"""Synthetic basketball-only validation; never published as sport results."""
import copy
import joblib
import numpy as np
from test_model import synthetic_rows
from sportslab.nba_context import features,definitions
from sportslab.research import build,fit,label

def test_context_features_cannot_see_own_or_future_outcomes():
 rows=synthetic_rows(100);a,names=features(rows);changed=copy.deepcopy(rows);day=rows[48]['date']
 for r in changed:
  if r['date']>=day:r.update(home_score='300',away_score='0',outcome='home')
 b,_=features(changed)
 for left,right in zip(a,b):
  if left[0]['date']<=day:assert left[1]==right[1]
 assert any(x[1][-10:]!=y[1][-10:] for x,y in zip(a,b) if x[0]['date']>day)
 assert a[0][1][names.index('shared_prediction_error_variance')]==.5

def test_same_date_context_is_batch_independent():
 rows=synthetic_rows(100);a,_=features(rows);b,_=features(list(reversed(rows)));other={r['event_id']:x[-10:] for r,x,_ in b}
 for r,x,_ in a:assert np.allclose(x[-10:],other[r['event_id']])

def test_context_blend_preserves_retained_inputs_and_serializes(tmp_path):
 catalog=definitions();assert len(catalog)==36 and len({label(s) for s in catalog})==36
 rows=synthetic_rows(800);context,names=build(rows,20,'context_nba_context');base,_=build(rows,20,'context_nba_feedback');X=np.array([x for _,x,_ in context]);Y=np.array([r['outcome']=='home' for r,_,_ in context]);days=[r['date'] for r,_,_ in context]
 from sportslab.research import NBAContextBlend
 assert np.allclose(NBAContextBlend.base_inputs(X),np.array([x for _,x,_ in base]))
 spec=next(s for s in catalog if s['kind']=='nba_context_blend');m=fit(spec,X,Y,days,'NBA');p=m.predict_proba(X[-8:]);assert np.isfinite(p).all() and np.allclose(p.sum(axis=1),1)
 path=tmp_path/'context.joblib';joblib.dump(m,path);assert np.allclose(joblib.load(path).predict_proba(X[-8:]),p)

def test_nba_context_challenger_is_accepted_by_live_inference():
 from sportslab.lifecycle import probabilities
 rows=synthetic_rows(800);spec={'kind':'logistic','variant':'context_nba_context','window':20,'c':.03}
 built,_=build(rows,20,spec['variant']);X=np.array([x for _,x,_ in built]);y=np.array([r['outcome']=='home' for r,_,_ in built]);days=[r['date'] for r,_,_ in built]
 m=fit(spec,X,y,days,'NBA');p,results=probabilities({'model':m,'variant':spec['variant'],'window':20,'extra':False,'league':'NBA'},rows,rows[700]['date'])
 assert p and all(0<=v<=1 for v in p.values())


def test_schedule_features_are_causal_and_batch_independent():
 from sportslab.nba_context import schedule_features
 rows=synthetic_rows(100);first,names=schedule_features(rows);changed=copy.deepcopy(rows);cut=rows[50]['date']
 for r in changed:
  if r['date']>=cut:r.update(home_score='300',away_score='0',outcome='home')
 second,_=schedule_features(changed)
 for a,b in zip(first,second):
  if a[0]['date']<=cut:assert a[1]==b[1]
 reverse,_=schedule_features(list(reversed(rows)));lookup={r['event_id']:x for r,x,n in reverse}
 for r,x,n in first:assert np.allclose(x,lookup[r['event_id']])
 assert len(names)==len(first[0][1])


def test_schedule_model_live_inference_and_serialization(tmp_path):
 from sportslab.lifecycle import probabilities
 rows=synthetic_rows(800);spec={'kind':'logistic','variant':'context_nba_schedule','window':20,'c':.03}
 built,names=build(rows,20,spec['variant']);X=np.array([x for r,x,n in built]);y=np.array([r['outcome']=='home' for r,x,n in built]);days=[r['date'] for r,x,n in built]
 model=fit(spec,X,y,days,'NBA');path=tmp_path/'schedule.joblib';joblib.dump(model,path)
 p,_=probabilities({'model':joblib.load(path),'variant':spec['variant'],'window':20,'extra':False,'league':'NBA'},rows,rows[700]['date'])
 assert p and all(0<=v<=1 for v in p.values())


def test_nba_schedule_compression_and_offseason_reset():
 from sportslab.nba_context import schedule_features
 rows=synthetic_rows(4)
 for r,day in zip(rows,['2026-01-01','2026-01-02','2026-01-04','2026-10-01']):r.update(date=day,home='A',away='B',home_score='110',away_score='90',outcome='home',neutral='0')
 rows[2].update(away='C');rows[3].update(away='C')
 built,names=schedule_features(rows)
 assert built[2][1][names.index('three_in_four_difference')]==1
 assert built[2][1][names.index('recent_margin_difference')]>0
 assert built[3][1][names.index('recent_margin_difference')]==0
 assert built[3][1][names.index('three_in_four_difference')]==0
