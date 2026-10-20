"""One-time official NHL schedule backfill; current 21-day refresh handles subsequent updates."""
from datetime import date, timedelta
import json
import os
import time
from sportslab.data import connect, ingest
from sportslab.refresh import fetch, game, FEEDS
root=os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private');db=connect(root)
start=date(2024,10,1);end=date.today();day=start;total=0;manifests=[]
while day<=end:
 raw,m=fetch(root,FEEDS['NHL']['url']+day.isoformat(),'NHL');manifests.append(m);rows=[]
 for week_day in json.loads(raw).get('gameWeek',[]):
  for r in week_day.get('games',[]):
   if r.get('gameType') not in (2,3) or r['gameState'] not in ('OFF','FINAL'):continue
   h,a=r['homeTeam'],r['awayTeam']
   rows.append(game('nhl-'+str(r['id']),'NHL',week_day['date'],h['abbrev'],a['abbrev'],h['score'],a['score'],FEEDS['NHL']['description']))
 if rows:total+=ingest(db,list({r['event_id']:r for r in rows}.values()))
 day+=timedelta(days=7)
 time.sleep(.1)
print('NHL weekly source batches processed; idempotent accepted rows:',total)
with db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('nhl_backfill_manifest',json.dumps(manifests)))
db.close()
