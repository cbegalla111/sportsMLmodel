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
