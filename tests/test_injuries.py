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

def test_nba_production_is_pregame_team_matched_and_missing_is_flagged(tmp_path):
 from sportslab.injuries import nba_production_context,FEATURES,NBA_FEATURES,NBA_SCHEMA
 p=prediction(parse(payload(),'NBA',NOW))
 player={'id':'123','games':[{'event_id':'past','team':'A','start_time':(NOW-timedelta(days=2)).isoformat(),'values':{'Points':25.,'Rebounds':8.,'Assists':6.}}, {'event_id':'future','team':'A','start_time':(NOW+timedelta(hours=1)).isoformat(),'values':{'Points':100.,'Rebounds':50.,'Assists':50.}}, {'event_id':'wrong-team','team':'C','start_time':(NOW-timedelta(days=1)).isoformat(),'values':{'Points':100.,'Rebounds':50.,'Assists':50.}}]}
 context=nba_production_context(p,[player],NOW);team=context['teams']['A'];assert team['totals']['absent_points']==25
 assert team['players'][0]['sample_games']==1 and team['players'][0]['game_ids']==['past']
 record_research(tmp_path,'NBA',[p],[],NOW,players=[player]);path=tmp_path/'public-injuries/research/NBA.json';row=json.loads(path.read_text())['events']['123']
 assert row['feature_schema']==NBA_SCHEMA and len(row['features'])==len(NBA_FEATURES)
 assert row['features'][len(FEATURES)]==-25 and row['injury_players']['A'][0]['status']=='Out'
 first=path.read_text();player['games'][0]['values']['Points']=80
 record_research(tmp_path,'NBA',[p],[],NOW+timedelta(minutes=1),players=[player]);assert path.read_text()==first
 missing=nba_production_context(p,[],NOW);assert missing['teams']['A']['totals']['unknown_production']==1

def test_injury_schema_mixing_is_not_silently_imputed_and_corrupt_ledger_preserved(tmp_path):
 from sportslab.injuries import NBA_SCHEMA
 rows=[{'id':'old','date':'2026-11-01','outcome':1,'features':[0.]*5},{'id':'new','date':'2026-11-02','outcome':None,'features':[0.]*11,'feature_schema':NBA_SCHEMA}]
 r=review(rows);assert r['recorded']==2 and r['settled_all']==1 and r['settled']==0 and r['pending']==1
 assert r['training_recorded']==1 and r['excluded_legacy_schema']==1
 directory=tmp_path/'public-injuries/research';directory.mkdir(parents=True);path=directory/'NBA.json';path.write_text('damaged history')
 p=prediction(parse(payload(),'NBA',NOW));report=record_research(tmp_path,'NBA',[p],[],NOW)
 assert report['status']=='injury ledger needs recovery' and path.read_text()=='damaged history'

def test_compressed_injury_archives_retain_timestamp_and_payload_hash(tmp_path):
 import gzip,hashlib
 refresh(tmp_path,NOW,lambda url:payload())
 files=list((tmp_path/'public-injuries/archives/NBA').glob('*.json.gz'));assert len(files)==1
 with gzip.open(files[0],'rt',encoding='utf-8') as f:archived=json.load(f)
 assert archived['observed_at']==NOW.isoformat()
 assert archived['sha256']==hashlib.sha256(json.dumps(archived['payload'],sort_keys=True).encode()).hexdigest()
 p=prediction(parse(payload(),'NBA',NOW));report=record_research(tmp_path,'NBA',[p],[],NOW)
 assert report['archive_reports']==1 and report['recorded']==1 and report['pending']==1

def test_corrected_official_start_cannot_label_postgame_injury_data(tmp_path):
 p=prediction(parse(payload(),'NBA',NOW));record_research(tmp_path,'NBA',[p],[],NOW)
 final={'event_id':'espn-nba-123','outcome':'home','start_time':(NOW-timedelta(hours=1)).isoformat()}
 r=record_research(tmp_path,'NBA',[],[final],NOW+timedelta(hours=5))
 assert r['pending']==0 and r['unscored']==1 and r['settled']==0


def test_matchup_resolves_nfl_and_nhl_schedule_abbreviations():
 from sportslab.injuries import matchup
 from datetime import datetime,timedelta,timezone
 now=datetime(2026,11,8,12,tzinfo=timezone.utc)
 def report(league,team):return {'league':league,'status':'ok','checked':now.isoformat(),'valid_until':(now+timedelta(hours=8)).isoformat(),'teams':{team:[{'player':'Player','category':'unavailable','status':'Out'}]}}
 nfl=matchup(report('NFL','New England Patriots'),'NE','KC',now)
 assert nfl['status']=='review_required' and len(nfl['teams']['NE'])==1
 assert nfl['affected_players'][0]['team']=='NE'
 nhl=matchup(report('NHL','Boston Bruins'),'BOS','NYR',now)
 assert nhl['status']=='review_required' and len(nhl['teams']['BOS'])==1
 assert not nhl['model_adjusted']
