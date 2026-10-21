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
