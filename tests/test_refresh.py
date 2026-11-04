import csv
import io
import json
from sportslab.refresh import refresh_one
from sportslab.data import connect, load
from sportslab import refresh

def test_refresh_drops_all_market_columns_and_is_idempotent(tmp_path,monkeypatch):
 raw=b'game_id,season,gameday,home_team,away_team,home_score,away_score,location,home_moneyline,spread_line\n2020_01_A_B,2020,2020-09-01,A,B,21,14,Home,-999,40\n'
 monkeypatch.setattr(refresh,'fetch',lambda root,url,league:(raw,{'url':'synthetic mocked feed, not real','fetched':'2020-09-02','sha256':'test'}))
 refresh_one(tmp_path,'NFL');refresh_one(tmp_path,'NFL')
 rows=load(connect(tmp_path),'NFL');assert len(rows)==1
 assert not any('moneyline' in k or 'spread' in k for k in rows[0]);assert rows[0]['home_score']=='21'

def test_feed_error_preserves_existing_history(tmp_path,monkeypatch):
 def failed(*a):raise ValueError('source unavailable')
 monkeypatch.setattr(refresh,'fetch',failed)
 statuses=refresh.run(tmp_path)
 assert all(s['status']=='error' for s in statuses)
 assert all('source unavailable'==s['error'] for s in statuses)
 assert connect(tmp_path).execute('SELECT COUNT(*) FROM games').fetchone()[0]==0


def test_mlb_excludes_tied_preseason_without_losing_regular_games(tmp_path,monkeypatch):
 def item(eid,kind,hs,aws):
  return {'gamePk':eid,'gameType':kind,'officialDate':'2025-06-01','status':{'abstractGameState':'Final'},'teams':{'home':{'team':{'name':'Test A'},'score':hs},'away':{'team':{'name':'Test B'},'score':aws}}}
 payload={'dates':[{'date':'2025-06-01','games':[item(1,'S',0,0),item(2,'R',3,2)]}]}
 monkeypatch.setattr(refresh,'fetch',lambda *a:(json.dumps(payload).encode(),{'url':'synthetic mocked MLB feed','fetched':'2025-06-02','sha256':'test'}))
 result=refresh_one(tmp_path,'MLB');rows=load(connect(tmp_path),'MLB')
 assert len(rows)==1 and rows[0]['event_id']=='mlb-2';assert result['status']=='ok'

def test_nfl_eastern_kickoff_converts_to_utc_with_daylight_saving():
 assert refresh.nfl_start({'gameday':'2026-10-22','gametime':'20:15'})=='2026-10-23T00:15:00+00:00'
 assert refresh.nfl_start({'gameday':'2026-12-20','gametime':'20:15'})=='2026-12-21T01:15:00+00:00'
 assert refresh.nfl_start({'gameday':'2026-10-22','gametime':''}) is None

def test_nba_schedule_includes_far_future_and_preseason_without_training_it(monkeypatch,tmp_path):
 from sportslab.refresh import refresh_nba_mirror
 from datetime import date
 raw=b'id,date,season_type,home_display_name,away_display_name,status_type_completed,status_type_state,home_score,away_score,neutral_site,time_valid\n1,2027-03-01T00:00Z,2,A,B,false,pre,,,false,true\n2,2026-12-01T00:00Z,1,A,B,false,pre,,,false,true\n3,2026-10-01T00:00Z,1,A,B,true,post,100,90,false,true\n'
 monkeypatch.setattr('sportslab.refresh.fetch',lambda *a:(raw,{'url':'https://raw.githubusercontent.com/source'}))
 rows,fixtures,_=refresh_nba_mirror(tmp_path,date(2026,11,4))
 assert not rows and len(fixtures)==2
 assert fixtures[0]['forecast_eligible'] and not fixtures[1]['forecast_eligible']

def test_nhl_full_season_is_deduplicated_and_keeps_far_future(monkeypatch,tmp_path):
 from sportslab.refresh import nhl_full_schedule
 from datetime import date
 import json
 game={'id':2026021000,'gameDate':'2027-03-01','startTimeUTC':'2027-03-01T00:00Z','gameState':'FUT','gameType':2,'homeTeam':{'abbrev':'SEA'},'awayTeam':{'abbrev':'CGY'}}
 calls=[]
 def source(root,url,league):calls.append(url);return json.dumps({'games':[game]}).encode(),{'url':url}
 monkeypatch.setattr('sportslab.refresh.fetch',source)
 fixtures,_=nhl_full_schedule(tmp_path,date(2026,11,4))
 assert len(calls)==32 and len(fixtures)==1 and fixtures[0]['date']=='2027-03-01'

def test_mlb_published_schedule_crosses_into_next_year(monkeypatch,tmp_path):
 from sportslab.refresh import refresh_one
 from datetime import date
 import json
 class FixedDate(date):
  @classmethod
  def today(cls):return cls(2026,11,4)
 monkeypatch.setattr('sportslab.refresh.date',FixedDate);calls=[]
 def source(root,url,league):
  calls.append(url)
  games=[] if 'startDate=2027-' not in url else [{'date':'2027-03-01','games':[{'gamePk':123,'gameType':'R','officialDate':'2027-03-01','gameDate':'2027-03-01T23:00Z','status':{'abstractGameState':'Preview','detailedState':'Scheduled'},'teams':{'home':{'team':{'name':'Synthetic A'}},'away':{'team':{'name':'Synthetic B'}}}}]}]
  return json.dumps({'dates':games}).encode(),{'url':url,'sha256':'test-only'}
 monkeypatch.setattr('sportslab.refresh.fetch',source)
 status=refresh_one(tmp_path,'MLB')
 assert any('startDate=2027-01-01' in url for url in calls)
 assert len(status['upcoming'])==1 and status['upcoming'][0]['date']=='2027-03-01'
 assert status['schedule_horizon_days']==365 and status['accepted_rows']==0
