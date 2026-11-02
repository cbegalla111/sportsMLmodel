"""Public final box-score observations for descriptive player-prop research.
No odds, betting lines, injury assumptions or predictive probabilities are inferred.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import urllib.request

PATHS={'NBA':'basketball/nba','WNBA':'basketball/wnba','MLB':'baseball/mlb','NFL':'football/nfl','NHL':'hockey/nhl'}
MARKETS={
 'NBA':{'Points':'points','Rebounds':'rebounds','Assists':'assists','Threes made':'threePointFieldGoalsMade-threePointFieldGoalsAttempted','Steals':'steals','Blocks':'blocks'},
 'NFL':{'Passing yards':'passingYards','Passing TDs':'passingTouchdowns','Rushing yards':'rushingYards','Receiving yards':'receivingYards','Receptions':'receptions'},
 'MLB':{'Hits':'hits','Home runs':'homeRuns','Runs':'runs','RBIs':'RBIs','Pitcher strikeouts':'strikeouts'},
 'NHL':{'Shots on goal':'shotsTotal','Goals':'goals','Assists':'assists','Saves':'saves'},
}
MARKETS['WNBA']=MARKETS['NBA']
BASE='https://site.api.espn.com/apis/site/v2/sports/'

def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Courtside-public-research/1.0'}),timeout=15) as response:
  return json.load(response)

def parse_box(payload,league,event):
 if not payload.get('header',{}).get('competitions',[{}])[0].get('status',{}).get('type',{}).get('completed'):return []
 output={}
 for team in payload.get('boxscore',{}).get('players',[]):
  for group in team.get('statistics',[]):
   keys=group.get('keys',[])
   for player in group.get('athletes',[]):
    if player.get('didNotPlay'):continue
    athlete=player.get('athlete',{});identity=str(athlete.get('id',''))
    if not identity or not athlete.get('displayName'):continue
    stats=dict(zip(keys,player.get('stats',[])));values={}
    for label,key in MARKETS[league].items():
     # Baseball strikeouts in batting are not pitcher strikeouts.
     if league=='MLB' and ((label=='Pitcher strikeouts') != (group.get('name')=='pitching')):continue
     raw=stats.get(key)
     if raw is None:continue
     try:
      value=float(str(raw).split('-')[0]) if label=='Threes made' else float(raw)
      if math.isfinite(value) and value>=0:values[label]=value
     except (ValueError,TypeError):continue
    if league in ('NBA','WNBA') and all(k in values for k in ('Points','Rebounds','Assists')):
     values['Points + rebounds + assists']=sum(values[k] for k in ('Points','Rebounds','Assists'))
    if not values:continue
    row=output.setdefault(identity,{'player_id':identity,'player':athlete['displayName'],'team':team.get('team',{}).get('displayName',''),'event_id':str(event['id']),'start_time':event['date'],'source':BASE+PATHS[league]+'/summary?event='+str(event['id']),'values':{}})
    row['values'].update(values)
 return list(output.values())

def refresh(root,asof=None,fetcher=fetch,cap=160):
 asof=asof or datetime.now(timezone.utc);directory=Path(root)/'public-props';directory.mkdir(parents=True,exist_ok=True)
 result={'checked':asof.isoformat(),'kind':'Historical game-log research; custom lines only. No live sportsbook feed.','leagues':{}}
 for league,path in PATHS.items():
  file=directory/(league+'.json')
  try:cache=json.loads(file.read_text()) if file.exists() else {}
  except (ValueError,OSError):cache={}
  error=None;pending=0
  try:
   boards=directory/(league+'-boards.json')
   try:days=json.loads(boards.read_text()) if boards.exists() else {}
   except (ValueError,OSError):days={}
   span=120 if league=='WNBA' else 60
   dates=[(asof-timedelta(days=i)).strftime('%Y%m%d') for i in range(span)]
   def scoreboard(day):
    if day in days and day<=(asof-timedelta(days=2)).strftime('%Y%m%d'):return day,days[day],None
    try:return day,fetcher(BASE+path+'/scoreboard?dates='+day+'&limit=1000').get('events',[]),None
    except Exception as exc:return day,days.get(day,[]),type(exc).__name__
   with ThreadPoolExecutor(max_workers=8) as pool:
    for day,events_on_day,failure in pool.map(scoreboard,dates):
     if failure:error='Some schedule dates could not be refreshed; collected coverage is incomplete.'
     else:days[day]=events_on_day
   days={k:v for k,v in days.items() if k in dates}
   boards.write_text(json.dumps(days,separators=(',',':')))
   events=[e for day in dates for e in days.get(day,[]) if e.get('status',{}).get('type',{}).get('completed') and e.get('date','')<asof.isoformat() and e.get('season',{}).get('type') in (None,2,3)]
   events=list({str(e['id']):e for e in events}.values())
   ineligible={str(e['id']) for day in dates for e in days.get(day,[]) if e.get('season',{}).get('type') not in (None,2,3)}
   cache={k:v for k,v in cache.items() if k not in ineligible}
   events.sort(key=lambda e:e['date'],reverse=True)
   todo=[e for e in events if str(e['id']) not in cache];pending=max(0,len(todo)-cap)
   def collect(e):
    try:
     rows=parse_box(fetcher(BASE+path+'/summary?event='+str(e['id'])),league,e)
     return str(e['id']),rows,None
    except Exception as exc:return str(e['id']),[],type(exc).__name__
   with ThreadPoolExecutor(max_workers=8) as pool:
    for identity,rows,failure in pool.map(collect,todo[:cap]):
     if rows:cache[identity]=rows
     elif failure:error='Some box scores could not be refreshed; retained observations remain available.'
   if not events:error='No completed games returned in the collection window.'
  except Exception as exc:error='Source refresh unavailable ('+type(exc).__name__+'); retained observations remain available.'
  cutoff=(asof-timedelta(days=180)).isoformat()
  cache={k:v for k,v in cache.items() if v and v[0]['start_time']>=cutoff}
  temporary=file.with_suffix('.tmp');temporary.write_text(json.dumps(cache,allow_nan=False,separators=(',',':')));temporary.replace(file)
  players={}
  for rows in cache.values():
   for row in rows:
    if row['start_time']>=asof.isoformat():continue
    player=players.setdefault(row['player_id'],{'id':row['player_id'],'name':row['player'],'team':row['team'],'games':[]})
    player['games'].append({k:row[k] for k in ('event_id','start_time','team','source','values')})
  for player in players.values():
   player['games'].sort(key=lambda g:g['start_time'],reverse=True);player['games']=player['games'][:30];player['team']=player['games'][0]['team']
  result['leagues'][league]={'players':sorted(players.values(),key=lambda p:p['name']),'games':len(cache),'error':error,'pending_games':pending,'source':BASE+path+'/scoreboard','checked':asof.isoformat()}
 (directory/'snapshot.json').write_text(json.dumps(result,allow_nan=False,separators=(',',':')))
 return {league:{'games':data['games'],'players':len(data['players']),'error':data['error']} for league,data in result['leagues'].items()}

def load_public(root):
 file=Path(root)/'public-props'/'snapshot.json'
 try:
  return json.loads(file.read_text()) if file.exists() else {'leagues':{},'kind':'Player game logs have not been collected yet.'}
 except (ValueError,OSError):
  return {'leagues':{},'kind':'Player game-log cache is unavailable; the next scheduled collection will retry.'}
