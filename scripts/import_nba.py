"""Fetch only historical results from a documented CC BY 4.0 dataset."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.request
from sportslab.data import connect, ingest, now
URL='https://raw.githubusercontent.com/fivethirtyeight/data/master/nba-elo/nbaallelo.csv'
root=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'))
root.mkdir(parents=True,exist_ok=True); root.chmod(0o700)
with urllib.request.urlopen(URL,timeout=90) as r: raw=r.read(30_000_001)
if len(raw)>30_000_000: raise ValueError('Source exceeds expected size')
archive=root/'sources'; archive.mkdir(exist_ok=True)
sha=hashlib.sha256(raw).hexdigest(); (archive/(sha+'.csv')).write_bytes(raw)
rows=[]
for r in csv.DictReader(io.StringIO(raw.decode())):
 if r['lg_id']!='NBA' or r['game_location']!='H' or int(r['year_id'])<2005: continue
 # One home-side row per game. Exclude source Elo, forecasts and postgame fields.
 rows.append({'event_id':'538-'+r['game_id'],'league':'NBA','date':r['date_game'],'home':r['team_id'],'away':r['opp_id'],'home_score':r['pts'],'away_score':r['opp_pts'],'outcome':'home' if int(r['pts'])>int(r['opp_pts']) else 'away','neutral':'0','source':'FiveThirtyEight NBA Elo results; CC BY 4.0; upstream Basketball-Reference'})
# Source dates are documented as month/day/year in some snapshots.
from datetime import datetime
for r in rows:
 try: datetime.strptime(r['date'],'%Y-%m-%d')
 except ValueError: r['date']=datetime.strptime(r['date'],'%m/%d/%Y').date().isoformat()
db=connect(root); count=ingest(db,rows); db.close()
manifest={'url':URL,'sha256':sha,'fetched':now(),'accepted_rows':count,'date_min':min(r['date'] for r in rows),'date_max':max(r['date'] for r in rows),'filter':'NBA home rows, season >=2005; neutral games excluded','license':'CC BY 4.0','attribution':'FiveThirtyEight / Basketball-Reference; transformed to home/away result-only schema'}
(archive/'nba-manifest.json').write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest,indent=2))
