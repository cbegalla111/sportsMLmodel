"""Promotion tests use synthetic outcomes, never published sport data."""
from datetime import date,timedelta
import json
import joblib
import numpy as np
from sportslab.data import version
from sportslab.lifecycle import gate,prepare,record
from test_model import synthetic_rows

def test_gate_requires_new_sample_and_broad_improvement():
 y=np.array([0,1]*100);days=[(date(2020,1,1)+timedelta(days=i)).isoformat() for i in range(len(y))]
 old=np.where(y,.55,.45);better=np.where(y,.75,.25)
 assert gate(y[:10],old[:10],better[:10],days[:10])['status']=='collecting evidence'
 assert gate(y,old,better,days)['promote']
 assert not gate(y,old,old,days)['promote']
 assert not gate(y,old,1-better,days)['promote']
 assert not gate(y,old,better,['2020-01-01']*200)['promote']

def test_first_published_pick_is_immutable_and_settled_once(tmp_path):
 rows=synthetic_rows(120);original=tmp_path/'original.joblib';root=tmp_path/'state';report={'league':'NBA','selected':'elo_w20','dataset_sha256':version(rows),'last_date':rows[-1]['date']}
 joblib.dump({'model':None,'window':20,'extra':False,'digest':version(rows),'last_date':rows[-1]['date'],'league':'NBA'},original)
 champion,summary=prepare(root,rows,report,original)
 p={'id':'one','date':rows[0]['date'],'home':rows[0]['home'],'away':rows[0]['away'],'home_probability':.7 if rows[0]['outcome']=='home' else .3,'generated_at':'2009-01-01T00:00:00+00:00','model':'elo_w20','dataset_sha256':version(rows)}
 record(root,[p]);record(root,[dict(p,home_probability=1-p['home_probability'])])
 _,summary=prepare(root,rows,report,original)
 assert summary['live_record']=={'wins':1,'losses':0,'pending':0}
 assert summary['weights_trained_through']==rows[-1]['date']
 assert not summary['trial']
 assert json.loads((root/'state.json').read_text())['ledger']['one']['home_probability']==p['home_probability']

def test_loss_locks_challenger_without_immediately_changing_weights(tmp_path):
 rows=synthetic_rows(800);original=tmp_path/'original.joblib';root=tmp_path/'review';report={'league':'NBA','selected':'elo_w20','dataset_sha256':version(rows),'last_date':rows[-1]['date'],'final_test_start':rows[640]['date']}
 joblib.dump({'model':None,'window':20,'extra':False,'digest':version(rows),'last_date':rows[-1]['date'],'league':'NBA'},original)
 prepare(root,rows,report,original)
 r=rows[-1];record(root,[{'id':'miss','date':r['date'],'home':r['home'],'away':r['away'],'home_probability':.1 if r['outcome']=='home' else .9,'generated_at':'2009-01-01T00:00:00+00:00','model':'elo_w20','dataset_sha256':version(rows)}])
 champion,review=prepare(root,rows,report,original)
 assert review['trial']['after']==rows[-1]['date']
 assert champion['model'] is None and review['live_record']['losses']==1
 locked=(root/'challenger.joblib').read_bytes()
 champion,review=prepare(root,synthetic_rows(804),report,original)
 assert review['confirmation']['status']=='collecting evidence'
 assert champion['model'] is None
 assert (root/'challenger.joblib').read_bytes()==locked
 assert not review['confirmation']['promote']
 for c in review['research']['candidates']:
  for f in c['folds']:
   assert f['train_end']<f['validation_start']<=f['validation_end']<report['final_test_start']
