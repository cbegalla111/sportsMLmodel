"""Timestamped public injury context and prospective injury-model research.
Reported absences are evidence, not invented player-value coefficients.
"""
from datetime import datetime,timedelta,timezone
import hashlib
import json
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
   (archive/(asof.strftime('%Y%m%dT%H%M%S')+'-'+digest[:12]+'.json')).write_text(json.dumps({'observed_at':asof.isoformat(),'sha256':digest,'payload':payload}))
   cutoff=(asof-timedelta(days=180)).strftime('%Y%m%d')
   for old in archive.glob('*.json'):
    if old.name[:8]<cutoff:old.unlink()
  except Exception as exc:
   report=dict(previous,league=league,status='unavailable',attempted_at=asof.isoformat(),error='Injury source unavailable or invalid ('+str(exc)[:140]+'). Active status is unverified.')
  temporary=file.with_suffix('.tmp');temporary.write_text(json.dumps(report,allow_nan=False,separators=(',',':')));temporary.replace(file);leagues[league]=report
 result={'version':VERSION,'leagues':leagues};(directory/'snapshot.json').write_text(json.dumps(result,allow_nan=False,separators=(',',':')))
 return {k:{'status':v['status'],'players':sum(len(p) for p in v.get('teams',{}).values())} for k,v in leagues.items()}

def load_public(root):
 try:return json.loads((Path(root)/'public-injuries'/'snapshot.json').read_text())
 except (OSError,ValueError):return {'version':VERSION,'leagues':{}}

def matchup(report,home,away,asof=None):
 asof=asof or datetime.now(timezone.utc)
 try:fresh=report.get('status')=='ok' and stamp(report['checked'])<=asof<stamp(report['valid_until'])
 except (ValueError,KeyError,TypeError):fresh=False
 teams={team:report.get('teams',{}).get(team,[]) for team in (home,away)}
 affected=any(p['category']!='listed_active' for players in teams.values() for p in players)
 return {'version':VERSION,'status':'review_required' if fresh and affected else 'report_checked' if fresh else 'unverified','checked':report.get('checked'),'valid_until':report.get('valid_until'),'source':report.get('source'),'teams':teams,'model_adjusted':False,'probability_label':'Result-history baseline; no validated injury adjustment','note':'Reported absences and uncertain statuses require lineup review. No arbitrary probability penalty is applied.' if fresh else 'Fresh injury coverage is unavailable; absence from this report is not clearance.'}

def injury_features(p,context):
 import math
 def counts(team):
  rows=context['teams'][team];out=[r for r in rows if r['category']=='unavailable']
  return [len(out),sum(r['category']=='uncertain' for r in rows),sum(r['position']=='QB' for r in out) if p.get('league') in ('NFL','CFB') else 0,sum(r['position']=='G' for r in out) if p.get('league')=='NHL' else 0]
 h,a=counts(p['home']),counts(p['away']);prob=max(1e-6,min(1-1e-6,p['home_probability']))
 return [math.log(prob/(1-prob))]+[float(y-x) for x,y in zip(h,a)]

def record_research(root,league,predictions,results,asof=None):
 """Freeze first *observed* pregame injury features; never recreate yesterday's report."""
 asof=asof or datetime.now(timezone.utc);directory=Path(root)/'public-injuries'/'research';directory.mkdir(parents=True,exist_ok=True);path=directory/(league+'.json')
 try:state=json.loads(path.read_text()) if path.exists() else {'events':{}}
 except (OSError,ValueError):state={'events':{}}
 by_id={str(r['event_id']):r for r in results}
 for row in state['events'].values():
  if stamp(row['event_start_utc'])>asof:continue
  identity=row['id'];matches=[r for key,r in by_id.items() if key==identity or key.endswith('-'+identity.removeprefix('espn-'+league.lower()+'-'))]
  if len(matches)==1 and matches[0]['outcome'] in ('home','away'):
   row['outcome']=int(matches[0]['outcome']=='home')
 for p in predictions:
  context=p.get('injury_context',{})
  try:
   if context.get('status')=='unverified' or not context.get('checked') or not stamp(context['checked'])<=asof<stamp(p['event_start_utc'])<=asof+timedelta(hours=24):continue
   key=str(p['id'])
   if key not in state['events']:
    state['events'][key]={'id':key,'date':p['date'],'home':p['home'],'away':p['away'],'observed_at':asof.isoformat(),'event_start_utc':p['event_start_utc'],'injury_checked':context['checked'],'baseline_probability':p['home_probability'],'baseline_model':p['model'],'baseline_training_sha256':p['dataset_sha256'],'features':injury_features(p,context),'outcome':None}
  except (KeyError,ValueError,TypeError):continue
 path.write_text(json.dumps(state,allow_nan=False,separators=(',',':')))
 report=review(state['events'].values())
 return report

def review(events):
 """Research only. Original winner-model promotion gates remain in force."""
 rows=sorted([r for r in events if r.get('outcome') in (0,1)],key=lambda r:(r['date'],r['id']))
 report={'status':'collecting prospective injury observations','settled':len(rows),'minimum_settled':200,'feature_names':FEATURES,'production_adjustment':False,'note':'No injury probability adjustment is approved. A historical research comparison cannot replace the required future promotion checks.'}
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
