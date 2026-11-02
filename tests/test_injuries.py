"""Synthetic injury reports only; no synthetic observations are published."""
from datetime import datetime,timedelta,timezone
import json
import pytest
from sportslab.injuries import parse,refresh,load_public,matchup,record_research,injury_features,review
NOW=datetime(2026,11,2,20,tzinfo=timezone.utc)
def payload(status='Out',date=None):
 return {'timestamp':NOW.isoformat(),'injuries':[{'displayName':'A','injuries':[{'status':status,'date':date or NOW.isoformat(),'shortComment':'Test injury','athlete':{'displayName':'Player','position':{'abbreviation':'G'},'links':[{'href':'https://www.espn.com/nba/player/_/id/123/player'}]}}]}]}

def test_status_identity_and_source_freshness():
 r=parse(payload(),'NBA',NOW);p=r['teams']['A'][0]
 assert p['player_id']=='123' and p['category']=='unavailable'
 assert parse(payload('Doubtful'),'NBA',NOW)['teams']['A'][0]['category']=='uncertain'
 assert parse(payload('Day-To-Day'),'NBA',NOW)['teams']['A'][0]['category']=='uncertain'
 assert parse(payload('Active'),'NBA',NOW)['teams']['A'][0]['category']=='listed_active'
 with pytest.raises(ValueError):parse(dict(payload(),timestamp=(NOW-timedelta(hours=9)).isoformat()),'NBA',NOW)
 with pytest.raises(ValueError):parse(payload(date='2020-11-02T00:00Z'),'CFB',NOW)
 with pytest.raises(ValueError):parse({},'NBA',NOW)

def test_failure_preserves_history_but_does_not_mark_it_current(tmp_path):
 refresh(tmp_path,NOW,lambda url:payload())
 before=load_public(tmp_path)['leagues']['NBA']
 def offline(url):raise OSError('offline')
 refresh(tmp_path,NOW+timedelta(hours=1),offline)
 after=load_public(tmp_path)['leagues']['NBA']
 assert after['teams']==before['teams'] and after['checked']==before['checked']
 assert after['status']=='unavailable'
 assert matchup(after,'A','B',NOW+timedelta(hours=1))['status']=='unverified'
 assert matchup(before,'A','B',NOW)['status']=='review_required'
 assert matchup(before,'A','B',NOW+timedelta(hours=9))['status']=='unverified'

def prediction(report):
 return {'id':'123','league':'NBA','date':'2026-11-03','event_start_utc':(NOW+timedelta(hours=4)).isoformat(),'home':'A','away':'B','home_probability':.6,'model':'baseline','dataset_sha256':'public-test','injury_context':matchup(report,'A','B',NOW)}

def test_first_observed_context_frozen_and_after_start_not_created(tmp_path):
 p=prediction(parse(payload(),'NBA',NOW))
 record_research(tmp_path,'NBA',[p],[],NOW)
 path=tmp_path/'public-injuries'/'research'/'NBA.json';first=json.loads(path.read_text())
 p['home_probability']=.9
 record_research(tmp_path,'NBA',[p],[],NOW+timedelta(hours=1))
 assert json.loads(path.read_text())==first
 result={'event_id':'espn-nba-123','outcome':'away'}
 record_research(tmp_path,'NBA',[],[result],NOW+timedelta(hours=5))
 assert json.loads(path.read_text())['events']['123']['outcome']==0
 p['id']='late';record_research(tmp_path,'NBA',[p],[],NOW+timedelta(hours=5))
 assert 'late' not in json.loads(path.read_text())['events']

def test_guards_are_not_goalies_and_no_arbitrary_probability_change():
 p=prediction(parse(payload(),'NBA',NOW));features=injury_features(p,p['injury_context'])
 assert features[1]==-1 and features[-1]==0
 assert p['injury_context']['model_adjusted'] is False
 assert p['home_probability']==.6
 assert review([])['production_adjustment'] is False

def test_no_observation_for_far_future_or_missing_injury_coverage(tmp_path):
 p=prediction(parse(payload(),'NBA',NOW));p['event_start_utc']=(NOW+timedelta(days=7)).isoformat()
 record_research(tmp_path,'NBA',[p],[],NOW)
 assert json.loads((tmp_path/'public-injuries'/'research'/'NBA.json').read_text())['events']=={}

def test_chronological_research_cannot_promote_weights():
 rows=[]
 for i in range(240):
  rows.append({'id':str(i),'date':(NOW-timedelta(days=240-i)).date().isoformat(),'outcome':i%2,'features':[.4,float(i%3),0.,0.,0.],'baseline_probability':.6})
 r=review(rows)
 assert r['status']=='chronological research comparison only'
 assert r['baseline']['n']==60 and r['injury_challenger']['n']==60
 assert r['production_adjustment'] is False
