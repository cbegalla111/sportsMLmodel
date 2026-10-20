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
