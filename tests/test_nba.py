import copy
from datetime import date,timedelta
import numpy as np
from test_model import synthetic_rows
from sportslab.nba import feedback_features,later_era_audit
from sportslab.lifecycle import feedback_report


def test_feedback_features_exclude_current_same_day_and_future_outcomes():
 rows=synthetic_rows(200);original,names=feedback_features(rows);cut=rows[80]['date'];changed=copy.deepcopy(rows)
 for r in changed:
  if r['date']>=cut:r.update(outcome='home',home_score='140',away_score='80')
 altered,_=feedback_features(changed)
 assert len(names)==21
 assert all(a[1]==b[1] for a,b in zip(original,altered) if a[0]['date']<=cut)
 assert any(a[1]!=b[1] for a,b in zip(original,altered) if a[0]['date']>cut)
 reversed_rows=list(reversed(rows))
 reordered,_=feedback_features(reversed_rows)
 assert {r['event_id']:x[-6:] for r,x,_ in original}=={r['event_id']:x[-6:] for r,x,_ in reordered}


def test_confident_wrong_outcome_corrects_more_than_expected_win():
 row=dict(synthetic_rows(1)[0],home='A',away='B',date='2010-01-01',neutral='0',home_score='103',away_score='100',outcome='home')
 query=dict(row,event_id='query',date='2010-01-02',outcome='no_contest')
 won,_=feedback_features([row,query]);lost,_=feedback_features([dict(row,home_score='100',away_score='103',outcome='away'),query])
 i=won[-1][1][-5];j=lost[-1][1][-5]
 assert i>0 and j<0 and abs(j)>abs(i)


def test_future_queries_cannot_train_feedback_state():
 rows=synthetic_rows(160);q=dict(rows[-1],event_id='query',date='2010-03-01',outcome='no_contest')
 original,_=feedback_features(rows+[q]);extra=dict(q,event_id='extra',date='2010-02-28',home_score='999',away_score='0')
 added,_=feedback_features(rows+[extra,q]);a={r['event_id']:x for r,x,_ in original};b={r['event_id']:x for r,x,_ in added}
 assert all(a[k]==b[k] for k in a)


def test_feedback_scores_saved_picks_and_exposes_overconfident_misses():
 entries={str(i):dict(id=str(i),date='2020-01-01',home='A',away='B',home_probability=p,outcome=y,settled=True,generated_at='2019-12-31',model='test') for i,(p,y) in enumerate(((.9,'away'),(.8,'home'),(.6,'home'),(.4,'away')))}
 entries['pending']={'home_probability':.99,'settled':False}
 report=feedback_report(entries)
 assert report['n']==4 and report['metrics']['accuracy']==.75
 assert report['largest_misses'][0]['home_probability']==.9
 assert sum(b['n'] for b in report['confidence_bands'])==4
 assert report['accuracy_95'][0]<.75<report['accuracy_95'][1]
 assert feedback_report({})['metrics'] is None


def test_later_audit_does_not_use_current_season_or_change_sealed_test():
 year=date.today().year-(date.today().month<7);start=date(year-4,7,1);rows=synthetic_rows(6000)
 for i,r in enumerate(rows):r['date']=(start+timedelta(days=i//4)).isoformat()
 spec={'kind':'logistic','window':20,'variant':'context_baseline','c':.1,'decay':False}
 original=later_era_audit(rows,spec,spec,'2015-06-16');changed=copy.deepcopy(rows)
 for r in changed:
  if r['date']>=original['before']:r.update(home_score='500',away_score='0',outcome='home')
 assert later_era_audit(changed,spec,spec,'2015-06-16')==original
 assert original['previous']['validation']==original['selected']['validation']
 assert len(original['selected']['folds'])==3
 for f in original['selected']['folds']:assert f['train_end']<f['validation_start']<=f['validation_end']<original['before']


def test_hybrid_views_match_individually_built_contextual_inputs(tmp_path):
 import joblib
 from sportslab.nba import FeedbackBlend
 from sportslab.research import build,fit
 rows=synthetic_rows(400);hybrid,names=build(rows,20,'context_nba_hybrid');X=np.array([x for _,x,_ in hybrid]);left,right=FeedbackBlend.inputs(X)
 feedback,_=build(rows,20,'context_nba_feedback');form,_=build(rows,20,'context_form')
 assert len(names)==30
 assert np.allclose(left,np.array([x for _,x,_ in feedback]))
 assert np.allclose(right,np.array([x for _,x,_ in form]))
 y=np.array([r['outcome']=='home' for r in rows]);days=[r['date'] for r in rows]
 m=fit({'kind':'nba_blend','feedback_weight':.5},X,y,days,'NBA');p=m.predict_proba(X)
 assert np.allclose(p[:,1],.5*m.feedback.predict_proba(left)[:,1]+.5*m.form.predict_proba(right)[:,1])
 path=tmp_path/'blend.joblib';joblib.dump(m,path);assert np.allclose(p,joblib.load(path).predict_proba(X))


def test_recent_confirmation_excludes_archive_and_current_season():
 from sportslab.nba import recent_confirmation
 rows=synthetic_rows(6800)
 for i,r in enumerate(rows):r['date']=(date(2022,1,1)+timedelta(days=i//4)).isoformat()
 spec={'kind':'logistic','window':20,'variant':'context_nba_feedback','c':.03,'decay':False}
 old=recent_confirmation(rows,spec,spec);changed=copy.deepcopy(rows)
 for r in changed:
  if r['date']>='2026-07-01':r.update(home_score='500',away_score='0',outcome='home')
 assert recent_confirmation(changed,spec,spec)==old
 assert old['previous']['validation']==old['selected']['validation']
 assert old['train_end']<old['from'] and not old['passed']


def test_recent_artifact_uses_its_training_history_start_in_live_inference(tmp_path):
 import json,joblib
 from sportslab.data import connect,ingest,version
 from sportslab.model import estimate,prediction_context,fixture_inputs
 from sportslab.research import build,fit
 from sportslab.lifecycle import probabilities
 rows=synthetic_rows(800);cut=rows[200]['date'];recent=[r for r in rows if r['date']>=cut];built,names=build(recent,20,'context_nba_feedback');warm=np.array([n>=5 for _,_,n in built]);X=np.array([x for _,x,_ in built]);y=np.array([r['outcome']=='home' for r in recent]);model=fit({'kind':'logistic','c':.03},X[warm],y[warm],[r['date'] for r,keep in zip(recent,warm) if keep],'NBA')
 art={'model':model,'window':20,'extra':False,'variant':'context_nba_feedback','history_from':cut,'digest':version(recent),'training_event_ids':[r['event_id'] for r in recent],'last_date':recent[-1]['date'],'league':'NBA','names':names}
 db=connect(tmp_path);ingest(db,rows);(tmp_path/'models').mkdir();joblib.dump(art,tmp_path/'models/NBA-recent.joblib');report={'id':'NBA-recent','selected':'logistic_context_nba_feedback_w20_C0.03','outcome_rules':'Synthetic test only'}
 with db:db.execute('INSERT INTO experiments VALUES(?,?,?,?)',('NBA-recent','NBA','2020-01-01',json.dumps(report)))
 ctx=prediction_context(db,tmp_path,'NBA',True);assert min(r['date'] for r in ctx['rows'])==cut
 fixture={'date':'2010-07-21','home':'T0','away':'T1','neutral':'0'};inputs=fixture_inputs(recent,[fixture],20,variant='context_nba_feedback');x,_,_=next(iter(inputs.values()))
 direct=estimate(db,tmp_path,'NBA','T0','T1',fixture['date'],scenario=True,allow_updated_history=True)
 assert abs(direct['home_probability']-model.predict_proba(np.array([x]))[0,1])<1e-12
 baseline,_=probabilities(art,rows,cut);changed=copy.deepcopy(rows)
 for r in changed:
  if r['date']<cut:r.update(home_score='500',away_score='0',outcome='home')
 modified,_=probabilities(art,changed,cut)
 assert baseline==modified


def test_loss_refit_updates_data_but_not_selected_specification_or_cached_weights(tmp_path):
 import joblib
 from sportslab.nba import refit_recent_candidate
 rows=synthetic_rows(400)
 for i,r in enumerate(rows):r['date']=(date(2024,1,1)+timedelta(days=i//4)).isoformat()
 spec={'kind':'logistic','window':20,'variant':'context_nba_feedback','c':.03,'decay':False}
 cached={'model':None,'window':20,'extra':False,'variant':'context_nba_feedback','history_from':'2022-01-01','research_spec':spec,'selected':'feedback','last_date':rows[200]['date']}
 path=tmp_path/'nba-recent-challenger.joblib';joblib.dump(cached,path);original=path.read_bytes();fresh=refit_recent_candidate(tmp_path,rows)
 assert fresh['research_spec']==spec and fresh['last_date']==rows[-1]['date']
 assert len(fresh['training_event_ids'])==400 and fresh['model'] is not None
 assert path.read_bytes()==original
