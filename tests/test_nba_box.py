"""Synthetic box-score fixtures; never published as sports observations."""
import copy,json
from datetime import datetime,date,timedelta,timezone
import numpy as np
import pytest
from test_model import synthetic_rows
from sportslab.nba_box import observations,COLUMNS,game_metrics,box_features,attach,BoxBlend,saved_research


def values(score):
 fgm=min(40,int(score)//2);tpm=int(score)%2;ftm=score-2*fgm-tpm
 return [80.,float(fgm),float(tpm),20.,float(ftm+5),float(ftm),10.,30.,13.,float(score)]


def fixture_rows(n=200):
 rows=synthetic_rows(n);boxes={r['event_id']:{'date':r['date'],'home':r['home'],'away':r['away'],'home_values':values(float(r['home_score'])),'away_values':values(float(r['away_score']))} for r in rows}
 return rows,boxes


def source_pair():
 game=dict(synthetic_rows(1)[0],event_id='espn-nba-77',date='2025-06-23',home_score='105',away_score='101',outcome='home')
 pair=[]
 for side in ('home','away'):
  record={'game_id':77,'game_date_time':datetime(2025,6,22,20,tzinfo=timezone(timedelta(hours=-4))),'team_home_away':side,'team_display_name':game[side]}
  record.update(dict(zip(COLUMNS,values(float(game[side+'_score'])))));pair.append(record)
 return game,pair


def test_source_uses_utc_date_and_exact_identity_score_matches():
 game,pair=source_pair();found=observations(pair,{game['event_id']:game})
 assert list(found)==[game['event_id']] and found[game['event_id']]['date']=='2025-06-23'
 for field,value in (('team_display_name','wrong team'),('team_score',99),('game_date_time',datetime(2025,6,22,tzinfo=timezone.utc)),('field_goals_made',1000),('free_throws_made',None)):
  changed=copy.deepcopy(pair);changed[0][field]=value
  assert observations(changed,{game['event_id']:game})=={}
 # Raw total agrees with the result, but the shooting arithmetic is inconsistent.
 changed=copy.deepcopy(pair);changed[0]['field_goals_made']-=1
 assert observations(changed,{game['event_id']:game})=={}


def test_estimated_efficiency_formulas_and_nonstandard_short_games():
 a=[88,40,10,30,20,15,10,30,13,105];b=[86,38,9,25,19,16,9,31,11,101];m=game_metrics(a,b);poss=.5*(88-10+13+.44*20+86-9+11+.44*19)
 assert m[0]==pytest.approx(100*105/poss) and m[2]==pytest.approx(45/88)
 assert m[6]==pytest.approx(10/41) and m[-1]==pytest.approx(poss)
 with pytest.raises(ValueError,match='possession'):game_metrics([20,10,3,5,0,0,1,5,2,23],[18,9,2,4,0,0,1,5,2,20])


def test_box_features_never_use_same_date_or_future_statistics_and_keep_missing_games():
 rows,boxes=fixture_rows();enriched=attach(rows,boxes);one,names=box_features(enriched);cut=rows[80]['date'];changed=copy.deepcopy(enriched)
 for r in changed:
  if r['date']>=cut:
   r.update(home_score='150',away_score='80',outcome='home');r['_nba_box']['home_values']=values(150);r['_nba_box']['away_values']=values(80)
 two,_=box_features(changed)
 assert len(names)==35
 assert all(a[1]==b[1] for a,b in zip(one,two) if a[0]['date']<=cut)
 assert any(a[1][-14:]!=b[1][-14:] for a,b in zip(one,two) if a[0]['date']>cut)
 missing,_=box_features(rows)
 assert [r['event_id'] for r,_,_ in missing]==[r['event_id'] for r,_,_ in one]
 assert [n for _,_,n in missing]==[n for _,_,n in one]
 assert all(x[-3:]==[0.,0.,0.] for _,x,_ in missing)
 reverse,_=box_features(list(reversed(enriched)));lookup={r['event_id']:x[-14:] for r,x,_ in reverse}
 assert all(np.allclose(x[-14:],lookup[r['event_id']]) for r,x,_ in one)


def test_blend_inputs_match_separate_causal_views_and_serialization(tmp_path):
 import joblib
 from sportslab.research import build,fit
 rows,boxes=fixture_rows(400);rows=attach(rows,boxes);combined,names=build(rows,20,'context_nba_box_blend');X=np.array([x for _,x,_ in combined]);a,b=BoxBlend.inputs(X);left,_=build(rows,10,'context_nba_box');right,_=build(rows,20,'context_nba_feedback')
 assert len(names)==60
 assert np.allclose(a,np.array([x for _,x,_ in left])) and np.allclose(b,np.array([x for _,x,_ in right]))
 model=fit({'kind':'nba_box_blend','box_weight':.5},X,np.array([r['outcome']=='home' for r in rows]),[r['date'] for r in rows],'NBA');p=model.predict_proba(X);path=tmp_path/'model.joblib';joblib.dump(model,path)
 assert np.allclose(p,joblib.load(path).predict_proba(X)) and np.allclose(p.sum(axis=1),1)


def test_explicit_research_catalog_isolated_from_default_catalog(monkeypatch):
 from sportslab.research import review
 rows,boxes=fixture_rows(800);spec={'kind':'logistic','window':10,'variant':'context_nba_box','c':.03};report={'league':'NBA','selected':'elo_w20','final_test_start':rows[640]['date']}
 monkeypatch.setattr('sportslab.research.definitions',lambda league:(_ for _ in ()).throw(AssertionError('Default catalog must not run')))
 _,result=review(attach(rows,boxes),report,specifications=[spec])
 assert result['candidate_count']==result['completed_candidates']==1
 assert result['candidates'][1]['validation']['n']==result['incumbent']['validation']['n']


def test_cached_research_ignores_current_season_labels_but_refreshes_source_counts(tmp_path,monkeypatch):
 from sportslab.nba import recent_confirmation
 rows,boxes=fixture_rows(6000)
 for i,r in enumerate(rows):
  r['date']=(date(2022,1,1)+timedelta(days=i//4)).isoformat();boxes[r['event_id']]['date']=r['date']
 spec={'kind':'logistic','window':20,'variant':'context_nba_feedback','c':.03};previous={'best':{'name':'feedback','specification':spec},'confirmation':recent_confirmation(rows,spec,spec)};path=tmp_path/'nba-box-history.json';history={'observations':boxes,'manifests':[],'matched_games':len(boxes)};path.write_text(json.dumps(history))
 monkeypatch.setattr('sportslab.nba_box.candidates',lambda:[dict(kind='logistic',variant='context_nba_box',window=10,c=.03)])
 first=saved_research(tmp_path,rows,previous)
 monkeypatch.setattr('sportslab.research.review',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Current-season outcomes must not trigger historical reselection')))
 later=dict(rows[-1],event_id='new',date='2026-10-24');history['matched_games']+=1;path.write_text(json.dumps(history));second=saved_research(tmp_path,rows+[later],previous)
 assert second['confirmation']==first['confirmation'] and second['source_matched_games']==first['source_matched_games']+1
 assert second['raw_confirmation_sha256']==previous['confirmation']['cohort_sha256']
 assert not second['target_reached'] or second['confirmation']['selected']['validation']['accuracy']>=.7


def test_optional_source_failure_preserves_cached_observations(tmp_path,monkeypatch):
 from sportslab.nba_box import refresh_history
 path=tmp_path/'nba-box-history.json';path.write_text('{"observations": {}}');original=path.read_bytes()
 monkeypatch.setattr('sportslab.nba_box.fetch_history',lambda *a:(_ for _ in ()).throw(ValueError('source revision')))
 result=refresh_history(tmp_path,[])
 assert result['status']=='unavailable' and path.read_bytes()==original
 assert json.loads((tmp_path/'nba-box-feed.json').read_text())['status']=='unavailable'


def test_target_uses_retained_candidate_if_new_experiment_fails_confirmation():
 from sportslab.nba_box import target_summary
 previous={'validation':{'n':1322,'accuracy':904/1322}};experiment={'validation':{'n':1322,'accuracy':897/1322}}
 summary=target_summary({'previous':previous,'selected':experiment,'passed':False})
 assert summary['target_reference']==previous and summary['additional_correct_needed']==22
 assert not summary['candidate_accepted'] and not summary['target_reached']
 passed={'validation':{'n':1322,'accuracy':930/1322}}
 summary=target_summary({'previous':previous,'selected':passed,'passed':True})
 assert summary['target_reference']==passed and summary['additional_correct_needed']==0 and summary['target_reached']
