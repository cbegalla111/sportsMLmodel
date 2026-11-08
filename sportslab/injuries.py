"""Timestamped public injury context and prospective injury-model research.
Reported absences are evidence, not invented player-value coefficients.
"""
from datetime import datetime,timedelta,timezone
import hashlib
import gzip
import json
import math
from pathlib import Path
import re
import urllib.request

PATHS={'NBA':'basketball/nba','WNBA':'basketball/wnba','NFL':'football/nfl','MLB':'baseball/mlb','NHL':'hockey/nhl','CFB':'football/college-football'}
VERSION='injury-context-v1'
FEATURES=['baseline_log_odds','away_minus_home_absences','away_minus_home_uncertain','away_minus_home_qb_absences','away_minus_home_goalie_absences']

def stamp(value):
 if not isinstance(value,str):raise ValueError('Missing injury timestamp')
 dt=datetime.fromisoformat(value.replace('Z','+00:00'))
 if dt.tzinfo is None:raise ValueError('Injury timestamp needs timezone')
 return dt.astimezone(timezone.utc)

def category(status):
 status=str(status).strip().lower()
 if status in {'out','injured reserve','injury reserve','suspension','suspended','inactive','pup','physically unable to perform','non-football injury'} or 'injured list' in status:return 'unavailable'
 if status in {'active','healthy','available','cleared'}:return 'listed_active'
 return 'uncertain'

def parse(payload,league,asof):
 if not isinstance(payload.get('injuries'),list):raise ValueError('Missing injury list')
 source='https://site.api.espn.com/apis/site/v2/sports/'+PATHS[league]+'/injuries'
 source_time=stamp(payload['timestamp'])
 if not timedelta(0)<=asof-source_time<=timedelta(hours=8):raise ValueError('Source injury timestamp is stale or in the future')
 teams={};discarded=0
 for team in payload['injuries']:
  name=team.get('displayName') or team.get('team',{}).get('displayName')
  if not name:continue
  players={}
  for entry in team.get('injuries',[]):
   athlete=entry.get('athlete',{});identity=athlete.get('id')
   if not identity:
    for link in athlete.get('links',[]):
     match=re.search(r'https://www\.espn\.com/[^ ]*/_/id/(\d+)',link.get('href',''))
     if match:identity=match[1];break
   try:reported=stamp(entry['date'])
   except (ValueError,KeyError,TypeError):discarded+=1;continue
   if reported>asof or asof-reported>timedelta(days=180):discarded+=1;continue
   if not identity or not athlete.get('displayName'):discarded+=1;continue
   row={'player_id':str(identity),'player':athlete['displayName'],'team':name,'status':str(entry.get('status','Unknown')),'category':category(entry.get('status')),'reported_at':reported.isoformat(),'position':athlete.get('position',{}).get('abbreviation',''),'description':str(entry.get('shortComment',''))[:1000],'source':source}
   if str(identity) not in players or row['reported_at']>players[str(identity)]['reported_at']:players[str(identity)]=row
  teams[name]=list(players.values())
 total=sum(len(v) for v in teams.values())
 if discarded and not total:raise ValueError('Only stale or invalid injury records returned')
 return {'league':league,'status':'ok','checked':asof.isoformat(),'source_timestamp':source_time.isoformat(),'valid_until':(min(asof,source_time)+timedelta(hours=8)).isoformat(),'source':source,'teams':teams,'discarded_records':discarded,'coverage':'Listed players only; omission does not verify availability or starting role.'}

def fetch(url):
 with urllib.request.urlopen(url,timeout=20) as response:return json.load(response)

def refresh(root,asof=None,fetcher=fetch):
 asof=asof or datetime.now(timezone.utc);directory=Path(root)/'public-injuries';directory.mkdir(parents=True,exist_ok=True);leagues={}
 for league,path in PATHS.items():
  file=directory/(league+'.json')
  try:previous=json.loads(file.read_text()) if file.exists() else {}
  except (OSError,ValueError):previous={}
  try:
   payload=fetcher('https://site.api.espn.com/apis/site/v2/sports/'+path+'/injuries')
   report=parse(payload,league,asof)
   archive=directory/'archives'/league;archive.mkdir(parents=True,exist_ok=True)
   digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
   with gzip.open(archive/(asof.strftime('%Y%m%dT%H%M%S')+'-'+digest[:12]+'.json.gz'),'wt',encoding='utf-8') as compressed:json.dump({'observed_at':asof.isoformat(),'sha256':digest,'payload':payload},compressed)
   cutoff=(asof-timedelta(days=180)).strftime('%Y%m%d')
   for old in archive.glob('*.json*'):
    if old.name[:8]<cutoff:old.unlink()
  except Exception as exc:
   report=dict(previous,league=league,status='unavailable',attempted_at=asof.isoformat(),error='Injury source unavailable or invalid ('+str(exc)[:140]+'). Active status is unverified.')
  temporary=file.with_suffix('.tmp');temporary.write_text(json.dumps(report,allow_nan=False,separators=(',',':')));temporary.replace(file);leagues[league]=report
 result={'version':VERSION,'leagues':leagues};(directory/'snapshot.json').write_text(json.dumps(result,allow_nan=False,separators=(',',':')))
 return {k:{'status':v['status'],'players':sum(len(p) for p in v.get('teams',{}).values())} for k,v in leagues.items()}

def load_public(root):
 try:return json.loads((Path(root)/'public-injuries'/'snapshot.json').read_text())
 except (OSError,ValueError):return {'version':VERSION,'leagues':{}}

NFL_TEAMS=dict(zip('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WAS'.split(),['Arizona Cardinals','Atlanta Falcons','Baltimore Ravens','Buffalo Bills','Carolina Panthers','Chicago Bears','Cincinnati Bengals','Cleveland Browns','Dallas Cowboys','Denver Broncos','Detroit Lions','Green Bay Packers','Houston Texans','Indianapolis Colts','Jacksonville Jaguars','Kansas City Chiefs','Las Vegas Raiders','Los Angeles Chargers','Los Angeles Rams','Miami Dolphins','Minnesota Vikings','New England Patriots','New Orleans Saints','New York Giants','New York Jets','Philadelphia Eagles','Pittsburgh Steelers','San Francisco 49ers','Seattle Seahawks','Tampa Bay Buccaneers','Tennessee Titans','Washington Commanders']))

def team_injuries(report,name,league=None):
 from .grading import team
 league=league or report.get('league')
 canonical=NFL_TEAMS.get({'JAC':'JAX','LA':'LAR'}.get(name,name),name) if league=='NFL' else name
 matches=[rows for key,rows in report.get('teams',{}).items() if team(key)==team(canonical)]
 return matches[0] if len(matches)==1 else []

def matchup(report,home,away,asof=None,league=None):
 asof=asof or datetime.now(timezone.utc)
 try:fresh=report.get('status')=='ok' and stamp(report['checked'])<=asof<stamp(report['valid_until'])
 except (ValueError,KeyError,TypeError):fresh=False
 teams={team:team_injuries(report,team,league) for team in (home,away)}
 affected=any(p['category']!='listed_active' for players in teams.values() for p in players)
 return {'version':VERSION,'status':'review_required' if fresh and affected else 'report_checked' if fresh else 'unverified','checked':report.get('checked'),'valid_until':report.get('valid_until'),'source':report.get('source'),'teams':teams,'affected_players':[{**p,'team':team} for team,players in teams.items() for p in players if p.get('category')!='listed_active'] if fresh else [],'risk_level':'availability_review' if fresh and affected else 'coverage_unverified' if not fresh else 'report_checked','model_adjusted':False,'probability_label':'Result-history baseline; no validated injury adjustment','note':'Reported absences and uncertain statuses require lineup review. No arbitrary probability penalty is applied.' if fresh else 'Fresh injury coverage is unavailable; absence from this report is not clearance.'}

def injury_features(p,context):
 import math
 def counts(team):
  rows=context['teams'][team];out=[r for r in rows if r['category']=='unavailable']
  return [len(out),sum(r['category']=='uncertain' for r in rows),sum(r['position']=='QB' for r in out) if p.get('league') in ('NFL','CFB') else 0,sum(r['position']=='G' for r in out) if p.get('league')=='NHL' else 0]
 h,a=counts(p['home']),counts(p['away']);prob=max(1e-6,min(1-1e-6,p['home_probability']))
 return [math.log(prob/(1-prob))]+[float(y-x) for x,y in zip(h,a)]


NBA_SCHEMA='nba-production-v2'
NBA_FEATURES=FEATURES+['away_minus_home_absent_points','away_minus_home_absent_rebounds','away_minus_home_absent_assists','away_minus_home_uncertain_points','away_minus_home_unknown_production','away_minus_home_production_sample_games']

def nba_production_context(p,players,asof):
 """Prior observed production proxies, never a guessed injury point penalty."""
 index={str(player['id']):player for player in players};teams={}
 for team,injuries in p['injury_context']['teams'].items():
  totals={'absent_points':0.,'absent_rebounds':0.,'absent_assists':0.,'uncertain_points':0.,'unknown_production':0.,'production_sample_games':0.};profiles=[]
  for injury in injuries:
   if injury['category']=='listed_active':continue
   player=index.get(str(injury['player_id']),{});games=[]
   for game in player.get('games',[]):
    try:played=stamp(game['start_time'])
    except (KeyError,ValueError,TypeError):continue
    if game.get('team')==team and timedelta(0)<asof-played<=timedelta(days=30) and all(isinstance(game.get('values',{}).get(k),(int,float)) and math.isfinite(game['values'][k]) and game['values'][k]>=0 for k in ('Points','Rebounds','Assists')):games.append(game)
   games=sorted(games,key=lambda g:g['start_time'],reverse=True)[:10]
   profile={k:injury.get(k) for k in ('player_id','player','team','status','category','reported_at')};profile['sample_games']=len(games)
   if games:
    means={k:sum(g['values'][k] for g in games)/len(games) for k in ('Points','Rebounds','Assists')};profile.update(recent_means=means,latest_game=games[0]['start_time'],game_ids=[g['event_id'] for g in games])
    totals['production_sample_games']+=len(games)
    if injury['category']=='unavailable':
     for label,key in (('Points','absent_points'),('Rebounds','absent_rebounds'),('Assists','absent_assists')):totals[key]+=means[label]
    else:totals['uncertain_points']+=means['Points']
   else:totals['unknown_production']+=1
   profiles.append(profile)
  teams[team]={'totals':totals,'players':profiles}
 return {'schema':NBA_SCHEMA,'teams':teams,'note':'Recent observed production of listed players, not a projected point deduction. Missing production is flagged; starters, replacements and causal player value are unknown. Long-standing absences may already be reflected in team form.'}

def record_research(root,league,predictions,results,asof=None,players=None):
 """Freeze first *observed* pregame injury features; never recreate yesterday's report."""
 asof=asof or datetime.now(timezone.utc);directory=Path(root)/'public-injuries'/'research';directory.mkdir(parents=True,exist_ok=True);path=directory/(league+'.json')
 try:state=json.loads(path.read_text()) if path.exists() else {'events':{}}
 except (OSError,ValueError):
  return {'status':'injury ledger needs recovery','recorded':None,'pending':None,'settled':0,'minimum_settled':200,'production_adjustment':False,'note':'Existing injury history could not be read. It was preserved rather than reset; restore a verified runtime backup.'}
 if league=='NBA' and players is None:
  from .props import load_public as load_props
  props=load_props(root).get('leagues',{}).get('NBA',{})
  try:players=props.get('players',[]) if timedelta(0)<=asof-stamp(props.get('checked'))<=timedelta(hours=24) else []
  except (ValueError,TypeError):players=[]
 by_id={str(r['event_id']):r for r in results}
 for row in state['events'].values():
  if stamp(row['event_start_utc'])>asof:continue
  identity=row['id'];matches=[r for key,r in by_id.items() if key==identity or key.endswith('-'+identity.removeprefix('espn-'+league.lower()+'-'))]
  if len(matches)==1:
   final=matches[0];invalid=False
   if final.get('start_time'):invalid=not timedelta(0)<stamp(final['start_time'])-stamp(row['observed_at'])<=timedelta(hours=24)
   if invalid or final.get('state') in ('canceled','postponed') or final.get('outcome') in ('draw','no_contest'):
    row.update(outcome=None,grading_excluded=True,settled_no_decision=True,grading_status='unscored')
   elif final.get('outcome') in ('home','away'):
    row.update(outcome=int(final['outcome']=='home'),grading_excluded=False,settled_no_decision=False,grading_status='graded')
 for p in predictions:
  context=p.get('injury_context',{})
  try:
   if context.get('status')=='unverified' or not context.get('checked') or not stamp(context['checked'])<=asof<stamp(p['event_start_utc'])<=asof+timedelta(hours=24):continue
   key=str(p['id'])
   if key not in state['events']:
    row={'id':key,'date':p['date'],'home':p['home'],'away':p['away'],'observed_at':asof.isoformat(),'event_start_utc':p['event_start_utc'],'injury_checked':context['checked'],'baseline_probability':p['home_probability'],'baseline_model':p['model'],'baseline_training_sha256':p['dataset_sha256'],'features':injury_features(p,context),'outcome':None,'feature_schema':'injury-counts-v1','injury_players':context['teams']}
    if league=='NBA':
     production=nba_production_context(p,players or [],asof);row['production_context']=production;row['feature_schema']=NBA_SCHEMA
     h,a=[production['teams'][p[side]]['totals'] for side in ('home','away')]
     row['features'] += [a[k]-h[k] for k in ('absent_points','absent_rebounds','absent_assists','uncertain_points','unknown_production','production_sample_games')]
    state['events'][key]=row
  except (KeyError,ValueError,TypeError):continue
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(state,allow_nan=False,separators=(',',':')));temporary.replace(path)
 report=review(state['events'].values())
 captures=list(state['events'].values());times=[r['observed_at'] for r in captures]
 report.update(archive_reports=len(list((Path(root)/'public-injuries'/'archives'/league).glob('*.json*'))),first_capture_at=min(times) if times else None,last_capture_at=max(times) if times else None,records_with_player_production=sum(r.get('feature_schema')==NBA_SCHEMA for r in captures),recent_captures=[{k:r.get(k) for k in ('id','date','home','away','observed_at','event_start_utc','feature_schema','outcome','grading_status')} for r in sorted(captures,key=lambda r:r['observed_at'],reverse=True)[:8]])
 return report

def review(events):
 """Research only. Original winner-model promotion gates remain in force."""
 events=list(events);schema=NBA_SCHEMA if any(r.get('feature_schema')==NBA_SCHEMA for r in events) else 'injury-counts-v1'
 eligible=[r for r in events if r.get('feature_schema','injury-counts-v1')==schema]
 rows=sorted([r for r in eligible if r.get('outcome') in (0,1) and not r.get('grading_excluded')],key=lambda r:(r['date'],r['id']))
 report={'status':'collecting prospective injury observations','settled':len(rows),'minimum_settled':200,'recorded':len(events),'pending':sum(r.get('outcome') is None and not r.get('settled_no_decision') for r in events),'unscored':sum(bool(r.get('settled_no_decision')) for r in events),'settled_all':sum(r.get('outcome') in (0,1) for r in events),'training_recorded':len(eligible),'excluded_legacy_schema':len(events)-len(eligible),'feature_schema':schema,'feature_names':NBA_FEATURES if schema==NBA_SCHEMA else FEATURES,'production_adjustment':False,'note':'No injury probability adjustment is approved. A historical research comparison cannot replace the required future promotion checks.'}
 if len(rows)<200:return report
 import numpy as np
 from sklearn.linear_model import LogisticRegression
 from sklearn.pipeline import make_pipeline
 from sklearn.preprocessing import StandardScaler
 from sklearn.metrics import log_loss,brier_score_loss,accuracy_score
 cutoff=rows[int(len(rows)*.75)]['date'];train=[r for r in rows if r['date']<cutoff];test=[r for r in rows if r['date']>=cutoff]
 if len(train)<100 or len(test)<50 or len({r['outcome'] for r in train})<2:return report
 model=make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=1000,random_state=7))
 model.fit([r['features'] for r in train],[r['outcome'] for r in train]);y=np.array([r['outcome'] for r in test]);prob=model.predict_proba([r['features'] for r in test])[:,1];base=np.array([r['baseline_probability'] for r in test])
 def metrics(p):return {'n':len(test),'accuracy':float(accuracy_score(y,p>=.5)),'log_loss':float(log_loss(y,p,labels=[0,1])),'brier':float(brier_score_loss(y,p))}
 old,new=metrics(base),metrics(prob)
 report.update(status='chronological research comparison only',validation_from=cutoff,baseline=old,injury_challenger=new,passes_historical_gate=new['log_loss']<=old['log_loss']-.002 and new['brier']<=old['brier'] and new['accuracy']>=old['accuracy'])
 return report
