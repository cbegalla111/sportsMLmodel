"""Idempotent public-feed ingestion. Raw source archives never become feature tables."""
import csv
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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

ESPN_PATHS={'NBA':'basketball/nba','WNBA':'basketball/wnba','CFB':'football/college-football','UFC':'mma/ufc'}
ESPN_SOURCES={league:'ESPN public scoreboard; completed results and scheduled events only' for league in ESPN_PATHS}
for _league,_path in ESPN_PATHS.items():
 FEEDS.setdefault(_league,{'url':'https://site.api.espn.com/apis/site/v2/sports/'+_path+'/scoreboard','description':ESPN_SOURCES[_league]})

def espn_url(league):
 return 'https://site.api.espn.com/apis/site/v2/sports/'+ESPN_PATHS[league]+'/scoreboard'

def espn_events(payload,league,source_url,today):
 """Use explicit final/winner fields; never ingest odds or current career statistics."""
 records=[];upcoming=[]
 for event in payload.get('events',[]):
  if league in ('NBA','WNBA') and event.get('season',{}).get('type') not in (None,2,3,5):continue
  # UFC's competitions are individual bouts, not the whole fight card.
  for bout in event.get('competitions',[]):
   competitors=bout.get('competitors',[])
   if len(competitors)!=2:continue
   if league=='UFC':
    competitors=sorted(competitors,key=lambda c:str(c.get('id','')))
    h,a=competitors
   else:
    sides={c.get('homeAway'):c for c in competitors}
    if not all(k in sides for k in ('home','away')):continue
    h,a=sides['home'],sides['away']
   name=lambda c: c.get('athlete' if league=='UFC' else 'team',{}).get('displayName')
   hn,an=name(h),name(a)
   if not hn or not an:continue
   start=bout.get('date') or event.get('date');day=start[:10] if start else None
   if not day:continue
   identity='espn-'+league.lower()+'-'+str(bout['id'])
   status=bout.get('status',event.get('status',{})).get('type',{})
   if status.get('completed') and day<=today.isoformat():
    if league=='UFC':
     # Winner flags represent outcomes; 1–0 is an encoding, never a fight score.
     if h.get('winner') is True:hs,aws,outcome=1,0,'home'
     elif a.get('winner') is True:hs,aws,outcome=0,1,'away'
     else:hs,aws,outcome=0,0,'no_contest'
    else:
     try:hs,aws=float(h['score']),float(a['score'])
     except (ValueError,KeyError,TypeError):continue
     outcome='draw' if hs==aws else 'home' if hs>aws else 'away'
     if outcome=='draw' and league in ('NBA','WNBA'):continue
    row=game(identity,league,day,hn,an,hs,aws,ESPN_SOURCES[league],'1' if league=='UFC' or bout.get('neutralSite') else '0')
    row['outcome']=outcome;records.append(row)
   elif status.get('state')=='pre' and today.isoformat()<=day<=(today+timedelta(days=14)).isoformat():
    upcoming.append({'id':identity,'start_time':start,'date':day,'home':hn,'away':an,'neutral':'1' if league=='UFC' or bout.get('neutralSite') else '0','confirmed_source':True,'source':source_url})
 return records,upcoming

def refresh_espn(root,league,db,today):
 records=[];upcoming=[];manifests=[]
 if league=='NBA':
  return refresh_nba_mirror(root,today)
 if league=='CFB':
  return refresh_cfb_mirror(root,today)
 if league!='UFC':
  # Basketball/CFB reject date ranges. Their scoreboard accepts a season year.
  for year in range(2022,today.year+1):
   key=f'espn_year_v2_{league}_{year}'
   if year<today.year and db.execute('SELECT 1 FROM settings WHERE key=?',(key,)).fetchone():continue
   url=espn_url(league)+f'?dates={year}&limit=1000'+('&groups=80' if league=='CFB' else '')
   raw,manifest=fetch(root,url,league);payload=json.loads(raw)
   if len(payload.get('events',[]))>=1000:raise ValueError('Season response may be truncated')
   found,fixtures=espn_events(payload,league,url,today)
   if found:ingest(db,found)
   records.extend(found);upcoming.extend(fixtures);manifests.append(manifest)
   if year<today.year:
    with db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,now()))
 else:
  # UFC supports date ranges and nests individual bouts in each fight card.
  import calendar
  for year in range(2022,today.year+1):
   for month in range(1,13):
    start=date(year,month,1)
    if start>today:break
    end=date(year,month,calendar.monthrange(year,month)[1]);key=f'espn_month_{league}_{year}_{month}'
    if end<today-timedelta(days=35) and db.execute('SELECT 1 FROM settings WHERE key=?',(key,)).fetchone():continue
    url=espn_url(league)+f'?dates={start:%Y%m%d}-{min(end,today):%Y%m%d}&limit=1000'
    raw,manifest=fetch(root,url,league);payload=json.loads(raw)
    if len(payload.get('events',[]))>=1000:raise ValueError('Scoreboard response may be truncated')
    found,_=espn_events(payload,league,url,today)
    if found:ingest(db,found)
    records.extend(found);manifests.append(manifest)
    if end<today-timedelta(days=35):
     with db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,now()))
  url=espn_url(league)+f'?dates={today:%Y%m%d}-{today+timedelta(days=14):%Y%m%d}&limit=1000'
  raw,manifest=fetch(root,url,league);found,upcoming=espn_events(json.loads(raw),league,url,today);records.extend(found);manifests.append(manifest)

 return records,upcoming,manifests

CFB_MIRROR='https://raw.githubusercontent.com/sportsdataverse/cfbfastR-cfb-data/main/cfb/schedules/parquet/cfb_schedule_{year}.parquet'
CFB_FIXTURES='https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main/schedules/csv/cfb_schedules_{year}.csv'

def refresh_cfb_mirror(root,today):
 import pyarrow.parquet as pq
 records=[];fixtures=[];manifests=[];teams={}
 columns=['game_id','game_date','neutral_site','home_id','away_id','home_team','away_team','home_score','away_score','status']
 # Small season files provide complete results; select no ratings or market fields.
 for year in range(2022,today.year+1):
  raw,m=fetch(root,CFB_MIRROR.format(year=year),'CFB');manifests.append(m)
  for r in pq.read_table(io.BytesIO(raw),columns=columns).to_pylist():
   teams[str(r['home_id'])]=r['home_team'];teams[str(r['away_id'])]=r['away_team']
   day=str(r['game_date'])[:10]
   if day>today.isoformat() or r['status'] not in ('STATUS_FINAL','STATUS_FINAL_OVERTIME'):continue
   if r['home_score'] is None or r['away_score'] is None:continue
   records.append(game('espn-cfb-'+str(r['game_id']),'CFB',day,r['home_team'],r['away_team'],float(r['home_score']),float(r['away_score']),ESPN_SOURCES['CFB'],'1' if r['neutral_site'] else '0'))
 raw,m=fetch(root,CFB_FIXTURES.format(year=today.year),'CFB');manifests.append(m)
 for r in csv.DictReader(io.StringIO(raw.decode())):
  if r.get('completed')=='TRUE':continue
  start=r.get('start_date','');day=start[:10]
  if not today.isoformat()<=day<=(today+timedelta(days=14)).isoformat():continue
  h,a=teams.get(r['home_id']),teams.get(r['away_id'])
  if not h or not a:continue
  fixtures.append({'id':'espn-cfb-'+r['game_id'],'date':day,'start_time':start if r.get('start_time_tbd')=='FALSE' else None,'home':h,'away':a,'neutral':'1' if r.get('neutral_site')=='TRUE' else '0','confirmed_source':True,'source':m['url']})
 return records,fixtures,manifests

NBA_MIRROR='https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba/schedules/nba_schedule_master.csv'

def refresh_nba_mirror(root,today):
 raw,manifest=fetch(root,NBA_MIRROR,'NBA');records=[];fixtures=[]
 for r in csv.DictReader(io.StringIO(raw.decode())):
  day=r.get('date','')[:10]
  if day<'2022-01-01' or r.get('season_type') not in ('2','3','5'):continue
  h,a=r.get('home_display_name'),r.get('away_display_name')
  if not h or not a or h==a:continue
  eid='espn-nba-'+r['id'];neutral='1' if r.get('neutral_site')=='true' else '0'
  if r.get('status_type_completed')=='true' and day<=today.isoformat():
   try:hs,aws=float(r['home_score']),float(r['away_score'])
   except (ValueError,KeyError):continue
   if hs==aws:continue
   records.append(game(eid,'NBA',day,h,a,hs,aws,ESPN_SOURCES['NBA'],neutral))
  elif r.get('status_type_state')=='pre' and today.isoformat()<=day<=(today+timedelta(days=14)).isoformat():
   fixtures.append({'id':eid,'start_time':r['date'] if r.get('time_valid')=='true' else None,'date':day,'home':h,'away':a,'neutral':neutral,'confirmed_source':True,'source':NBA_MIRROR})
 return records,fixtures,[manifest]

def fetch(root,url,league):
 req=urllib.request.Request(url,headers={'User-Agent':'SportsMLLab/0.1 (private research; result-only importer)'})
 with urllib.request.urlopen(req,timeout=45) as r: raw=r.read(80_000_001)
 if len(raw)>80_000_000: raise ValueError('Source response exceeds 80 MB')
 sha=hashlib.sha256(raw).hexdigest(); dest=Path(root)/'sources'; dest.mkdir(exist_ok=True)
 (dest/(sha+'.raw')).write_bytes(raw)
 return raw,{'url':url,'fetched':now(),'sha256':sha,'league':league}

def nfl_start(row):
 try:
  return datetime.fromisoformat(row['gameday']+'T'+row['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()
 except (KeyError,TypeError,ValueError):return None

def game(eid,league,day,home,away,hs,aws,source,neutral='0'):
 return dict(event_id=eid,league=league,date=day,home=home,away=away,home_score=str(hs),away_score=str(aws),outcome='draw' if float(hs)==float(aws) else ('home' if float(hs)>float(aws) else 'away'),source=source,neutral=neutral)

def refresh_one(root,league):
 db=connect(root); records=[]; upcoming=[]; manifests=[]; src=FEEDS[league]['description']; today=date.today()
 if league in ESPN_PATHS:
  records,upcoming,manifests=refresh_espn(root,league,db,today)
 elif league=='NFL':
  raw,m=fetch(root,FEEDS[league]['url'],league); manifests.append(m)
  for r in csv.DictReader(io.StringIO(raw.decode())):
   if int(r['season'])<2005: continue
   if not r['home_score'] or not r['away_score'] or r['gameday']>today.isoformat():
    if today.isoformat()<=r['gameday']<=(today+timedelta(days=14)).isoformat(): upcoming.append({'id':r['game_id'],'start_time':nfl_start(r),'date':r['gameday'],'home':r['home_team'],'away':r['away_team'],'confirmed_source':True,'source':m['url']})
    continue
   records.append(game('nflverse-'+r['game_id'],league,r['gameday'],r['home_team'],r['away_team'],r['home_score'],r['away_score'],src,'1' if r['location']=='Neutral' else '0'))
 elif league=='MLB':
  # Three calendar seasons; idempotent refresh. Never import incomplete or suspended games.
  first_year=2024 if db.execute("SELECT COUNT(*) FROM games WHERE league='MLB'").fetchone()[0]==0 else today.year
  for year in range(first_year,today.year+1):
   url=FEEDS[league]['url']+f'?sportId=1&startDate={year}-01-01&endDate={min(today+timedelta(days=14),date(year,12,31)).isoformat()}'
   raw,m=fetch(root,url,league); manifests.append(m)
   for day in json.loads(raw).get('dates',[]):
    for r in day['games']:
     if r.get('gameType') not in ('R','F','D','L','W'): continue
     h,a=r['teams']['home'],r['teams']['away']; d=r.get('officialDate',day['date'])
     if r['status']['abstractGameState']=='Final' and 'score' in h and 'score' in a:
      records.append(game('mlb-'+str(r['gamePk']),league,d,h['team']['name'],a['team']['name'],h['score'],a['score'],src))
     elif r['status']['abstractGameState']=='Preview' and today.isoformat()<=d<=(today+timedelta(days=14)).isoformat(): upcoming.append({'id':str(r['gamePk']),'start_time':r.get('gameDate'),'date':d,'home':h['team']['name'],'away':a['team']['name'],'confirmed_source':True,'source':m['url']})
 elif league=='NBA':
  raw,m=fetch(root,FEEDS[league]['url'],league); manifests.append(m)
  for day in json.loads(raw)['leagueSchedule']['gameDates']:
   for r in day['games']:
    # Skip non-NBA/preseason/exhibition fixtures: IDs 002 regular, 004 playoffs, 005 play-in.
    if str(r['gameId'])[:3] not in ('002','004','005'): continue
    h,a=r['homeTeam'],r['awayTeam']; d=r['gameDateTimeUTC'][:10]
    if r['gameStatus']==3:
     records.append(game('nba-cdn-'+r['gameId'],league,d,h['teamTricode'],a['teamTricode'],h['score'],a['score'],src))
    elif r['gameStatus']==1 and today.isoformat()<=d<=(today+timedelta(days=14)).isoformat(): upcoming.append({'id':r['gameId'],'start_time':r.get('gameDateTimeUTC'),'date':d,'home':h['teamTricode'],'away':a['teamTricode'],'confirmed_source':True,'source':m['url']})
 elif league=='NHL':
  for offset in (-14,-7,0,7):
   raw,m=fetch(root,FEEDS[league]['url']+(today+timedelta(days=offset)).isoformat(),league); manifests.append(m)
   for day in json.loads(raw).get('gameWeek',[]):
    for r in day.get('games',[]):
     if r.get('gameType') not in (2,3): continue
     h,a=r['homeTeam'],r['awayTeam']; d=day['date']
     if r['gameState'] in ('OFF','FINAL'): records.append(game('nhl-'+str(r['id']),league,d,h['abbrev'],a['abbrev'],h['score'],a['score'],src))
     elif r['gameState']=='FUT' and today.isoformat()<=d: upcoming.append({'id':str(r['id']),'start_time':r.get('startTimeUTC'),'date':d,'home':h['abbrev'],'away':a['abbrev'],'confirmed_source':True,'source':m['url']})
 records=list({r['event_id']:r for r in records}.values())
 accepted=ingest(db,records) if records else 0
 status={'league':league,'status':'ok','checked':now(),'accepted_rows':accepted,'upcoming':upcoming,'manifests':manifests,'latest_result':db.execute('SELECT MAX(date) FROM games WHERE league=?',(league,)).fetchone()[0],'provider_url':NBA_MIRROR if league=='NBA' else CFB_MIRROR.format(year=today.year) if league=='CFB' else espn_url(league) if league in ESPN_PATHS else FEEDS[league]['url'],'last_success':now(),'feed_type':'Daily final results and upcoming schedules; not a live play-by-play stream','notes':'Final results only. Lineups, injury reports and sport-specific advanced inputs remain unconfirmed. Source revisions with conflicting immutable IDs require review.'}
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
