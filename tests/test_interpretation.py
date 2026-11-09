import math
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sportslab.interpretation import explain

def model():
 X=np.array([[i/10,(-1)**i] for i in range(60)]);y=np.array([int(i>30 or i%7==0) for i in range(60)])
 return make_pipeline(StandardScaler(),LogisticRegression()).fit(X,y)

def test_linear_contributions_reconstruct_prediction_and_reference_effects_are_exact():
 m=model();x=[4.,1.];p=float(m.predict_proba([x])[0,1]);r=explain(m,x,['elo_difference','win_rate_difference'],p,'Home','Away')
 assert r['status']=='available'
 total=r['intercept_log_odds']+sum(f['log_odds_contribution'] for f in r['ranked_factors'])
 assert abs(1/(1+math.exp(-total))-p)<1e-12
 for f in r['ranked_factors']:
  changed=x.copy();changed[['elo_difference','win_rate_difference'].index(f['factor'])]=f['reference_value']
  reference=float(m.predict_proba([changed])[0,1])
  assert abs(reference-f['probability_at_reference'])<1e-10
  assert abs(100*(p-reference)-f['probability_effect_pp'])<1e-10
 assert abs(r['ranked_factors'][0]['probability_effect_pp'])>=abs(r['ranked_factors'][1]['probability_effect_pp'])

def test_elo_interpretation_and_rest_guard_are_faithful():
 from sportslab.model import elo
 from sportslab.research import RestGuard
 x=[100.,1.,.2,3.,0.];r=explain(None,x,['elo_difference','home_advantage','win_rate_difference','scoring_margin_difference','rest_difference'],float(elo(np.array([x]))[0]),'Home','Away')
 assert r['status']=='available' and r['baseline_probability']==.5
 assert len([f for f in r['ranked_factors'] if abs(f['probability_effect_pp'])>1e-10])==2
 m=RestGuard(model());x=[4.,1.,999.];p=float(m.predict_proba(np.array([x]))[0,1])
 r=explain(m,x,['elo_difference','win_rate_difference','legacy_rest_training_only'],p,'Home','Away')
 assert r['status']=='available' and len(r['ranked_factors'])==2

def test_unsupported_or_inconsistent_models_never_invent_importance():
 m=model();assert explain(m,[4.,1.],['one','two'],.00001,'A','B')['status']=='unavailable'
 assert explain(object(),[1.],['one'],.5,'A','B')['status']=='unavailable'
