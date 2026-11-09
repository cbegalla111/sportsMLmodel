"""Reconcile recent saved picks using source-verified finals; never invent a winner."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json
import math
from pathlib import Path
import urllib.request
from .grading import identity,align

PATHS={'NBA':'basketball/nba','WNBA':'basketball/wnba','NFL':'football/nfl','CFB':'football/college-football','NHL':'hockey/nhl','UFC':'mma/ufc'}

def fetch(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SportsMLLab/0.1 (public result verification)'}),timeout=15) as response:return json.load(response)

def espn_competition(c,entry,url):
 if str(c.get('id'))!=identity(entry['id']):raise ValueError('Source event identity mismatch')
 status=c.get('status',{}).get('type',{});description=str(status.get('name',''))+' '+str(status.get('description',''))
 state='canceled' if 'cancel' in description.lower() else 'postponed' if 'postpon' in description.lower() else 'final' if status.get('completed') else 'in_progress' if status.get('state')=='in' else 'scheduled' if status.get('state')=='pre' else 'unknown'
 competitors=c.get('competitors',[])
 if len(competitors)!=2:raise ValueError('Source needs two competitors')
 if entry['league']=='UFC':
  h,a=sorted(competitors,key=lambda v:str(v['id']));name=lambda v:v.get('athlete',{}).get('displayName');hs=1 if h.get('winner') is True else 0;aws=1 if a.get('winner') is True else 0
  outcome='home' if hs else 'away' if aws else 'draw' if 'draw' in description.lower() else 'no_contest'
 else:
  sides={v.get('homeAway'):v for v in competitors};h,a=sides['home'],sides['away'];name=lambda v:v.get('team',{}).get('displayName')
  # Some summary responses put final scores in a displayValue object.
  score=lambda v:float(v.get('score',{}).get('displayValue')) if isinstance(v.get('score'),dict) else float(v['score'])
  hs,aws=(score(h),score(a)) if state=='final' else (None,None);outcome=('home' if hs>aws else 'away' if aws>hs else 'draw') if state=='final' else None
 record={'event_id':entry['id'],'league':entry['league'],'date':c['date'][:10],'home':name(h),'away':name(a),'home_score':hs,'away_score':aws,'outcome':outcome if state=='final' else None,'start_time':c['date'],'source':url,'state':state,'neutral':'1' if c.get('neutralSite') else '0'}
 if not record['home'] or not record['away'] or align(entry,record) is None:raise ValueError('Source opponents mismatch')
 if state=='final' and (not all(math.isfinite(v) and v>=0 for v in (hs,aws))):raise ValueError('Invalid final score')
 return record

def retrieve(entry,fetcher):
 league=entry['league'];eid=identity(entry['id'])
 if league=='MLB':
  url='https://statsapi.mlb.com/api/v1.1/game/'+eid+'/feed/live';d=fetcher(url);g=d['gameData'];teams=g['teams'];status=g['status'];box=d.get('liveData',{}).get('linescore',{}).get('teams',{})
  detail=status.get('detailedState','').lower();state='canceled' if 'cancel' in detail else 'postponed' if 'postpon' in detail or 'suspend' in detail else 'final' if status.get('abstractGameState')=='Final' else 'in_progress' if status.get('abstractGameState')=='Live' else 'scheduled'
  if str(d['gamePk'])!=eid:raise ValueError('MLB event identity mismatch')
  hs,aws=(float(box['home']['runs']),float(box['away']['runs'])) if state=='final' else (None,None)
  r={'event_id':entry['id'],'league':league,'date':g['datetime']['dateTime'][:10],'start_time':g['datetime']['dateTime'],'home':teams['home']['name'],'away':teams['away']['name'],'home_score':hs,'away_score':aws,'outcome':('home' if hs>aws else 'away' if aws>hs else 'draw') if state=='final' else None,'source':url,'state':state,'neutral':'0'}
  if align(entry,r) is None:raise ValueError('MLB opponents mismatch')
  return r
 if league=='NHL' and eid.isdigit() and len(eid)==10:
  url='https://api-web.nhle.com/v1/gamecenter/'+eid+'/landing';d=fetcher(url)
  if str(d['id'])!=eid:raise ValueError('NHL event identity mismatch')
  state='final' if d.get('gameState') in ('OFF','FINAL') else 'in_progress' if d.get('gameState') in ('LIVE','CRIT') else 'postponed' if d.get('gameScheduleState')=='PPD' else 'scheduled'
  h,a=d['homeTeam'],d['awayTeam'];hs,aws=(float(h['score']),float(a['score'])) if state=='final' else (None,None)
  r={'event_id':entry['id'],'league':league,'date':d['gameDate'],'start_time':d['startTimeUTC'],'home':h['abbrev'],'away':a['abbrev'],'home_score':hs,'away_score':aws,'outcome':('home' if hs>aws else 'away' if aws>hs else 'draw') if state=='final' else None,'source':url,'state':state,'neutral':'0'}
  if align(entry,r) is None:raise ValueError('NHL opponents mismatch')
  return r
 if league=='UFC':
  day=datetime.fromisoformat(entry['date']);url='https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates='+(day-timedelta(days=1)).strftime('%Y%m%d')+'-'+(day+timedelta(days=1)).strftime('%Y%m%d')+'&limit=1000';d=fetcher(url)
  for event in d.get('events',[]):
   for c in event.get('competitions',[]):
    if str(c.get('id'))==eid:
     c=dict(c,status=c.get('status',event.get('status')),date=c.get('date',event['date']));return espn_competition(c,entry,url)
  raise ValueError('Bout not returned by source')
 url='https://site.api.espn.com/apis/site/v2/sports/'+PATHS[league]+'/summary?event='+eid;d=fetcher(url)
 return espn_competition(d['header']['competitions'][0],entry,url)

def load(root):
 try:return json.loads((Path(root)/'public-results.json').read_text())
 except (OSError,ValueError):return {'events':{}}

def refresh(root,asof=None,fetcher=fetch):
 asof=asof or datetime.now(timezone.utc);data=load(root);pending={}
 for path in (Path(root)/'public-lifecycle').glob('*/state.json'):
  state=json.loads(path.read_text());entries=list(state.get('ledger',{}).values())+[e for ledger in state.get('policy_ledgers',{}).values() for e in ledger.values()]
  for e in entries:
   if e['date']>asof.date().isoformat():continue
   key=path.parent.name+':'+identity(e['id']);old=data['events'].get(key,{})
   if e.get('settled') and key not in data['events']:continue
   if path.parent.name=='NFL' and not identity(e['id']).isdigit():continue
   # Finals are rechecked daily; unresolved past games every update.
   if old.get('state')=='final' and (asof-datetime.fromisoformat(old['checked'])).total_seconds()<86400:continue
   pending.setdefault(key,dict(e,league=path.parent.name))
 def collect(item):
  key,e=item
  try:
   r=retrieve(e,fetcher)
   if r.get('state')=='final' and not all(isinstance(r.get(k),(float,int)) and math.isfinite(r[k]) and r[k]>=0 for k in ('home_score','away_score')):raise ValueError('Invalid source final score')
   r.update(checked=asof.isoformat());return key,r,None
  except Exception as exc:return key,None,type(exc).__name__
 failures=0
 with ThreadPoolExecutor(max_workers=6) as pool:
  ordered=sorted(pending.items(),key=lambda item:(item[1]['date'],item[0]),reverse=True)
  recent=[item for item in ordered if item[1]['date']>=(asof.date()-timedelta(days=10)).isoformat()][:200]
  older=[item for item in reversed(ordered) if item[1]['date']<(asof.date()-timedelta(days=10)).isoformat()][:50]
  for key,r,error in pool.map(collect,recent+older):
   if r:data['events'][key]=r
   else:failures+=1
 cutoff=(asof.date()-timedelta(days=12)).isoformat();data['events']={k:r for k,r in data['events'].items() if r['date']>=cutoff or r.get('state') in ('final','canceled','postponed')};data['checked']=asof.isoformat();data['failed_checks']=failures
 path=Path(root)/'public-results.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,allow_nan=False));tmp.replace(path)
 return {'checked':len(recent)+len(older),'queued_unchecked':max(0,len(pending)-len(recent)-len(older)),'finals':sum(r.get('state')=='final' for r in data['events'].values()),'failed_checks':failures}

def league_records(data,league):return [r for r in data.get('events',{}).values() if r.get('league')==league and r.get('state') in ('final','canceled','postponed')]
