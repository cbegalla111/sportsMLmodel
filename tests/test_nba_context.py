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
 catalog=definitions();assert len(catalog)==24 and len({label(s) for s in catalog})==24
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
