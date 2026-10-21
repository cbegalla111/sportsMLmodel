import copy
import numpy as np
from test_model import synthetic_rows
from sportslab.research import form_features,review,definitions

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
 assert result['candidate_count']==20
 for c in result['candidates']:
  assert c['validation']['n']==result['incumbent']['validation']['n']
  for f in c['folds']:assert f['train_end']<f['validation_start']<=f['validation_end']<report['final_test_start']
 assert result['best']['validation']['accuracy']>=result['incumbent']['validation']['accuracy']
 assert result['best']['validation']['brier']<=result['incumbent']['validation']['brier']
 built,_=form_features(rows,artifact['window']) if artifact['variant']=='form' else __import__('sportslab.model',fromlist=['features']).features(rows,artifact['window'])
 assert len(built[-1][1])==len(artifact['names'])
 # Mutating every archived test outcome cannot change candidate selection or CV scores.
 changed=copy.deepcopy(rows)
 for r in changed:
  if r['date']>=report['final_test_start']:r.update(outcome='home',home_score='400',away_score='0')
 _,second=review(changed,report)
 assert second['selected']==result['selected']
 assert second['candidates']==result['candidates']

def test_form_challenger_uses_identical_inputs_in_batched_and_direct_forecasts(tmp_path):
 import json
 import joblib
 import pytest
 from sportslab.data import connect,ingest,version,load
 from sportslab.model import estimate,fixture_inputs
 from sportslab.research import fit
 rows=synthetic_rows(800);db=connect(tmp_path);ingest(db,rows);rows=load(db,'NBA');built,names=form_features(rows);warm=np.array([v[2]>=5 for v in built]);X=np.array([v[1] for v in built]);y=np.array([v[0]['outcome']=='home' for v in built],dtype=int)
 spec={'kind':'logistic','c':.03,'variant':'form','window':20};m=fit(spec,X[warm],y[warm],[v[0]['date'] for v in built if v[2]>=5],'NBA')
 artifact={'model':m,'window':20,'variant':'form','extra':False,'names':names,'digest':version(rows),'last_date':rows[-1]['date'],'training_event_ids':[r['event_id'] for r in rows]}
 (tmp_path/'models').mkdir();joblib.dump(artifact,tmp_path/'models'/'NBA-test.joblib')
 report={'id':'NBA-test','selected':'logistic_form_w20_C0.03','outcome_rules':'Synthetic test only'}
 with db:db.execute('INSERT INTO experiments VALUES(?,?,?,?)',('NBA-test','NBA','2020-01-01',json.dumps(report)))
 fixture={'date':'2010-07-21','home':'T0','away':'T1','neutral':'0'}
 direct=estimate(db,tmp_path,'NBA','T0','T1',fixture['date'],scenario=True)
 inputs=fixture_inputs(rows,[fixture],20,variant='form');batch=estimate(db,tmp_path,'NBA','T0','T1',fixture['date'],scenario=True,prepared_inputs=inputs)
 assert direct['home_probability']==pytest.approx(batch['home_probability'])
 assert len(direct['factors'])==12
 assert direct['factors']==batch['factors']


def test_promoted_specification_is_used_as_incumbent():
 from sportslab.research import incumbent_spec
 report={'selected':'elo_w20'}
 champion={'selected':'boost_form_w20_leaves3','research_spec':{'kind':'boost','variant':'form','window':20,'leaves':3,'decay':False}}
 assert incumbent_spec(report,champion)==champion['research_spec']
