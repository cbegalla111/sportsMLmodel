"""Idempotent public-feed ingestion. Raw source archives never become feature tables."""
import csv
from datetime import date, timedelta
import hashlib
import io
import json
from pathlib import Path
import urllib.request
from .data import connect, ingest, now

FEEDS={
 'NFL':{'url':'https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv','description':'nflverse public schedules/results, documented by nflreadr load_schedules; select result columns only'},
 'MLB':{'url':'https://statsapi.mlb.com/api/v1/schedule','description':'MLB public Stats API, final game results and scheduled fixtures'},
 'NBA':{'url':'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json','description':'NBA public CDN season schedule; only final result fields are ingested'},
 'NHL':{'url':'https://api-web.nhle.com/v1/schedule/','description':'NHL public schedule API, rolling 21-day window; CSV required for initial long history'},
}

def fetch(root,url,league):
 req=urllib.request.Request(url,headers={'User-Agent':'SportsMLLab/0.1 (private research; result-only importer)'})
 with urllib.request.urlopen(req,timeout=45) as r: raw=r.read(40_000_001)
 if len(raw)>40_000_000: raise ValueError('Source response exceeds 40 MB')
 sha=hashlib.sha256(raw).hexdigest(); dest=Path(root)/'sources'; dest.mkdir(exist_ok=True)
 (dest/(sha+'.raw')).write_bytes(raw)
 return raw,{'url':url,'fetched':now(),'sha256':sha,'league':league}

def game(eid,league,day,home,away,hs,aws,source,neutral='0'):
 return dict(event_id=eid,league=league,date=day,home=home,away=away,home_score=str(hs),away_score=str(aws),outcome='draw' if float(hs)==float(aws) else ('home' if float(hs)>float(aws) else 'away'),source=source,neutral=neutral)

def refresh_one(root,league):
 db=connect(root); records=[]; upcoming=[]; manifests=[]; src=FEEDS[league]['description']; today=date.today()
 if league=='NFL':
  raw,m=fetch(root,FEEDS[league]['url'],league); manifests.append(m)
  for r in csv.DictReader(io.StringIO(raw.decode())):
   if int(r['season'])<2005: continue
   if not r['home_score'] or not r['away_score'] or r['gameday']>today.isoformat():
    if today.isoformat()<=r['gameday']<=(today+timedelta(days=14)).isoformat(): upcoming.append({'id':r['game_id'],'date':r['gameday'],'home':r['home_team'],'away':r['away_team'],'confirmed_source':True,'source':m['url']})
    continue
   records.append(game('nflverse-'+r['game_id'],league,r['gameday'],r['home_team'],r['away_team'],r['home_score'],r['away_score'],src,'1' if r['location']=='Neutral' else '0'))
 elif league=='MLB':
  # Three calendar seasons; idempotent refresh. Never import incomplete or suspended games.
  for year in range(today.year-2,today.year+1):
   url=FEEDS[league]['url']+f'?sportId=1&startDate={year}-01-01&endDate={min(today+timedelta(days=14),date(year,12,31)).isoformat()}'
   raw,m=fetch(root,url,league); manifests.append(m)
   for day in json.loads(raw).get('dates',[]):
    for r in day['games']:
     if r.get('gameType') not in ('R','F','D','L','W'): continue
     h,a=r['teams']['home'],r['teams']['away']; d=r.get('officialDate',day['date'])
     if r['status']['abstractGameState']=='Final' and 'score' in h and 'score' in a:
      records.append(game('mlb-'+str(r['gamePk']),league,d,h['team']['name'],a['team']['name'],h['score'],a['score'],src))
     elif r['status']['abstractGameState']=='Preview' and today.isoformat()<=d<=(today+timedelta(days=14)).isoformat(): upcoming.append({'id':str(r['gamePk']),'date':d,'home':h['team']['name'],'away':a['team']['name'],'confirmed_source':True,'source':m['url']})
 elif league=='NBA':
  raw,m=fetch(root,FEEDS[league]['url'],league); manifests.append(m)
  for day in json.loads(raw)['leagueSchedule']['gameDates']:
   for r in day['games']:
    # Skip non-NBA/preseason/exhibition fixtures: IDs 002 regular, 004 playoffs, 005 play-in.
    if str(r['gameId'])[:3] not in ('002','004','005'): continue
    h,a=r['homeTeam'],r['awayTeam']; d=r['gameDateTimeUTC'][:10]
    if r['gameStatus']==3:
     records.append(game('nba-cdn-'+r['gameId'],league,d,h['teamTricode'],a['teamTricode'],h['score'],a['score'],src))
    elif r['gameStatus']==1 and today.isoformat()<=d<=(today+timedelta(days=14)).isoformat(): upcoming.append({'id':r['gameId'],'date':d,'home':h['teamTricode'],'away':a['teamTricode'],'confirmed_source':True,'source':m['url']})
 elif league=='NHL':
  for offset in (-14,-7,0,7):
   raw,m=fetch(root,FEEDS[league]['url']+(today+timedelta(days=offset)).isoformat(),league); manifests.append(m)
   for day in json.loads(raw).get('gameWeek',[]):
    for r in day.get('games',[]):
     if r.get('gameType') not in (2,3): continue
     h,a=r['homeTeam'],r['awayTeam']; d=day['date']
     if r['gameState'] in ('OFF','FINAL'): records.append(game('nhl-'+str(r['id']),league,d,h['abbrev'],a['abbrev'],h['score'],a['score'],src))
     elif r['gameState']=='FUT' and today.isoformat()<=d: upcoming.append({'id':str(r['id']),'date':d,'home':h['abbrev'],'away':a['abbrev'],'confirmed_source':True,'source':m['url']})
 records=list({r['event_id']:r for r in records}.values())
 accepted=ingest(db,records) if records else 0
 status={'league':league,'status':'ok','checked':now(),'accepted_rows':accepted,'upcoming':upcoming,'manifests':manifests,'latest_result':max((r['date'] for r in records),default=None),'notes':'Final results only. Lineups, injury reports and sport-specific advanced inputs remain unconfirmed. Source revisions with conflicting immutable IDs require review.'}
 with db: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('feed_'+league,json.dumps(status)))
 db.close(); return status

def run(root):
 results=[]
 for league in FEEDS:
  try: results.append(refresh_one(root,league))
  except Exception as e:
   db=connect(root); previous=db.execute('SELECT value FROM settings WHERE key=?',('feed_'+league,)).fetchone()
   previous=json.loads(previous[0]) if previous else {}
   status=dict(previous,league=league,status='error',checked=now(),error=str(e))
   with db: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('feed_'+league,json.dumps(status)))
   db.close(); results.append(status)
 return results
