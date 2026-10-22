import copy
import numpy as np
import pytest
from test_model import synthetic_rows
from sportslab.research import form_features,profile_features,review,definitions

def test_form_features_never_see_current_or_same_date_results():
 rows=synthetic_rows(160);original,_=form_features(rows);changed=copy.deepcopy(rows);cut=rows[80]['date']
 for r in changed:
  if r['date']>=cut:r.update(outcome='home',home_score='400',away_score='0')
 altered,_=form_features(changed)
 assert all(a[1]==b[1] for a,b in zip(original,altered) if a[0]['date']<=cut)
 assert any(a[1]!=b[1] for a,b in zip(original,altered) if a[0]['date']>cut)

def test_review_uses_identical_folds_and_excludes_original_test():
 rows=synthetic_rows(800);report={'league':'NBA','selected':'logistic_w20','final_test_start':rows[640]['date'],'last_date':rows[-1]['date']}
 artifact,result=review(rows,report)
 assert result['candidate_count']==40
 assert any(c['specification'].get('calibrate') for c in result['candidates'])
 assert any(c['specification'].get('elo_weight') for c in result['candidates'])
 for c in result['candidates']:
  if c['status']=='skipped':continue
  assert c['validation']['n']==result['incumbent']['validation']['n']
  for f in c['folds']:
   assert f['train_end']<f['validation_start']<=f['validation_end']<report['final_test_start']
   if 'calibration' in f:
    a=f['calibration'];assert a['base_train_end']<a['calibration_start']<=a['calibration_end']<f['validation_start']
 assert result['best']['validation']['accuracy']>=result['incumbent']['validation']['accuracy']
 assert result['best']['validation']['brier']<=result['incumbent']['validation']['brier']
 built,_=__import__('sportslab.research',fromlist=['build']).build(rows,artifact['window'],artifact['variant'])
 assert len(built[-1][1])==len(artifact['names'])
 # Mutating every archived test outcome cannot change candidate selection or CV scores.
 changed=copy.deepcopy(rows)
 for r in changed:
  if r['date']>=report['final_test_start']:r.update(outcome='home',home_score='400',away_score='0')
 _,second=review(changed,report)
 assert second['selected']==result['selected']
 assert second['candidates']==result['candidates']

@pytest.mark.parametrize('variant',['form','profile'])
def test_form_challenger_uses_identical_inputs_in_batched_and_direct_forecasts(tmp_path,variant):
 import json
 import joblib
 import pytest
 from sportslab.data import connect,ingest,version,load
 from sportslab.model import estimate,fixture_inputs
 from sportslab.research import fit
 rows=synthetic_rows(800);db=connect(tmp_path);ingest(db,rows);rows=load(db,'NBA');built,names=__import__('sportslab.research',fromlist=['build']).build(rows,20,variant);warm=np.array([v[2]>=5 for v in built]);X=np.array([v[1] for v in built]);y=np.array([v[0]['outcome']=='home' for v in built],dtype=int)
 spec={'kind':'logistic','c':.03,'variant':variant,'window':20};m=fit(spec,X[warm],y[warm],[v[0]['date'] for v in built if v[2]>=5],'NBA')
 artifact={'model':m,'window':20,'variant':variant,'extra':False,'names':names,'digest':version(rows),'last_date':rows[-1]['date'],'training_event_ids':[r['event_id'] for r in rows]}
 (tmp_path/'models').mkdir();joblib.dump(artifact,tmp_path/'models'/'NBA-test.joblib')
 report={'id':'NBA-test','selected':'logistic_form_w20_C0.03','outcome_rules':'Synthetic test only'}
 with db:db.execute('INSERT INTO experiments VALUES(?,?,?,?)',('NBA-test','NBA','2020-01-01',json.dumps(report)))
 fixture={'date':'2010-07-21','home':'T0','away':'T1','neutral':'0'}
 direct=estimate(db,tmp_path,'NBA','T0','T1',fixture['date'],scenario=True)
 inputs=fixture_inputs(rows,[fixture],20,variant=variant);batch=estimate(db,tmp_path,'NBA','T0','T1',fixture['date'],scenario=True,prepared_inputs=inputs)
 assert direct['home_probability']==pytest.approx(batch['home_probability'])
 assert len(direct['factors'])==(12 if variant=='form' else 17)
 assert direct['factors']==batch['factors']


def test_promoted_specification_is_used_as_incumbent():
 from sportslab.research import incumbent_spec
 report={'selected':'elo_w20'}
 champion={'selected':'boost_form_w20_leaves3','research_spec':{'kind':'boost','variant':'form','window':20,'leaves':3,'decay':False}}
 assert incumbent_spec(report,champion)==champion['research_spec']


def test_calibration_and_blending_remain_frozen_after_serialization(tmp_path):
 from datetime import date,timedelta
 import joblib
 from sportslab.research import fit
 rng=np.random.default_rng(7);X=rng.normal(size=(500,5));X[:,0]*=100;X[:,1]=1;y=rng.binomial(1,1/(1+np.exp(-X[:,0]/120)))
 days=[(date(2010,1,1)+timedelta(days=i//4)).isoformat() for i in range(500)]
 for option in ({'calibrate':'temperature'},{'calibrate':'sigmoid'},{'elo_weight':.25}):
  model=fit(dict(kind='logistic',c=.1,**option),X,y,days,'NBA');original=model.predict_proba(X[-20:]);path=tmp_path/'candidate.joblib';joblib.dump(model,path);loaded=joblib.load(path)
  assert np.allclose(original,loaded.predict_proba(X[-20:]))
  assert np.allclose(original.sum(axis=1),1)
  assert np.isfinite(original).all() and ((original>0)&(original<1)).all()
  if 'calibrate' in option:
   a=model.calibration_audit;assert a['base_train_end']<a['calibration_start']<=a['calibration_end']

def test_small_calibration_samples_are_explicitly_rejected():
 import pytest
 from sportslab.research import fit,InsufficientCalibration
 with pytest.raises(InsufficientCalibration):fit({'kind':'elo','calibrate':'temperature'},np.zeros((40,5)),np.array([0,1]*20),['2010-01-01']*40,'UFC')


def test_score_profiles_are_pregame_and_not_used_for_fight_encodings():
 import pytest
 rows=synthetic_rows(160);original,names=profile_features(rows);changed=copy.deepcopy(rows);cut=rows[80]['date']
 for r in changed:
  if r['date']>=cut:r.update(home_score='400',away_score='0',outcome='home')
 mutated,_=profile_features(changed)
 assert len(names)==17
 assert all(a[1]==b[1] for a,b in zip(original,mutated) if a[0]['date']<=cut)
 with pytest.raises(ValueError,match='physical scoring'):profile_features([dict(r,league='UFC') for r in rows])
 assert all(s['variant']!='profile' for s in definitions('UFC'))
