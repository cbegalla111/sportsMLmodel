"""Export only allowlisted public results + frozen models, never private app state."""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from urllib.parse import quote, urlparse
from .data import BASE, FEATURES, LEAGUES, connect, ingest, load, now, version
from .model import estimate, train, fixture_inputs
from .lifecycle import prepare, record
from .refresh import FEEDS, ESPN_PATHS, ESPN_SOURCES, espn_url

PUBLIC_SOURCES={
 'NBA':('538-','FiveThirtyEight NBA Elo results; CC BY 4.0; upstream Basketball-Reference'),
 'NFL':('nflverse-',FEEDS['NFL']['description']),
 'MLB':('mlb-',FEEDS['MLB']['description']),
 'NHL':('nhl-',FEEDS['NHL']['description']),
}
RULES='Conditional on a decisive eventual winner, including overtime. NFL ties and UFC draws/no contests are excluded. Not unconditional sportsbook settlement probabilities.'

def parse_time(value):
 stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
 if stamp.tzinfo is None: raise ValueError('Timestamp needs timezone')
 return stamp.astimezone(timezone.utc)

def public_rows(db,league):
 prefix,source=PUBLIC_SOURCES.get(league,('',None));accepted=[]
 for r in load(db,league):
  approved=(source is not None and r['event_id'].startswith(prefix) and r['source']==source) or (league in ESPN_PATHS and r['event_id'].startswith('espn-'+league.lower()+'-') and r['source']==ESPN_SOURCES[league]) or (league=='NBA' and r['event_id'].startswith('nba-cdn-') and r['source']==FEEDS['NBA']['description'])
  if not approved:continue
  # Never export uploaded extra fields even if a row uses a public source label.
  accepted.append({key:r[key] for key in BASE})
 return accepted

def export_snapshot(source_root,artifacts,asof=None):
 asof=asof or datetime.now(timezone.utc)
 if asof.tzinfo is None:raise ValueError('Export time must be timezone-aware')
 asof=asof.astimezone(timezone.utc);today=asof.date();artifacts=Path(artifacts)
 source=sqlite3.connect('file:'+quote(str((Path(source_root)/'lab.sqlite3').resolve()))+'?mode=ro',uri=True)
 snapshot={'schema_version':1,'generated_at':asof.isoformat(),'valid_until':(asof+timedelta(hours=24)).isoformat(),'rules':RULES,'mode':'public read-only model outputs','update_schedule':'Daily at 11:17 UTC via GitHub Actions; runs can be delayed by GitHub.','leagues':[],'notes':['Original final tests stay sealed. Champion weights change only after a loss-triggered prospective improvement check.','Injuries, starters, pitchers, goalies, weather and lineups are unconfirmed.','Scores and rolling result history only. No sportsbook-derived model features.','Forecasts expire at a source-verified event start time, or at the start of the event date when only a date is available.']}
 with tempfile.TemporaryDirectory(prefix='sportsml-public-') as temporary:
  isolated=connect(temporary)
  for league in LEAGUES:
   rows=public_rows(source,league)
   if rows:ingest(isolated,rows)
   feed_record=source.execute('SELECT value FROM settings WHERE key=?',('feed_'+league,)).fetchone()
   feed=json.loads(feed_record[0]) if feed_record else {}
   feed_fresh=False
   try:feed_fresh=feed.get('status')=='ok' and timedelta(0)<=asof-parse_time(feed['checked'])<=timedelta(hours=24)
   except (KeyError,TypeError,ValueError):pass
   item={'name':league,'result_count':len(rows),'data_from':rows[0]['date'] if rows else None,'data_through':rows[-1]['date'] if rows else None,'sources':sorted({r['source'] for r in rows}),'feed_checked':feed.get('checked'),'feed_last_success':feed.get('last_success'),'feed_provider':feed.get('provider_url',espn_url(league) if league in ESPN_PATHS else FEEDS[league]['url']),'feed_error':feed.get('error') if feed.get('status')!='ok' else None,'feed_type':feed.get('feed_type','Daily final results and upcoming schedules; not live play-by-play'),'schedule':feed.get('upcoming',[]) if feed_fresh else [],'lifecycle':None,'feed_status':'fresh' if feed_fresh else ('unavailable' if not feed or feed.get('status')!='ok' else 'stale'),'benchmark':None,'predictions':[],'withheld':[],'recent_results':rows[-20:][::-1],'status':'not validated','limitation':'No verified public dataset and fitted model available.','candidate_features':FEATURES[league],'teams':[]}
   reports=[p for p in sorted(artifacts.glob(league+'-*.json')) if not p.name.endswith('-heldout.json')]
   from collections import defaultdict
   teams=defaultdict(list)
   for game in rows:
    if game['outcome'] not in ('home','away'):continue
    for side,opponent in (('home','away'),('away','home')):
     teams[game[side]].append({'date':game['date'],'opponent':game[opponent],'win':game['outcome']==side,'scored':float(game[side+'_score']),'allowed':float(game[opponent+'_score'])})
   for team,games in sorted(teams.items()):
    recent=games[-20:]
    item['teams'].append({'name':team,'games':len(games),'last_game':games[-1]['date'],'window_n':len(recent),'wins':sum(g['win'] for g in recent),'scored_per_game':sum(g['scored'] for g in recent)/len(recent),'allowed_per_game':sum(g['allowed'] for g in recent)/len(recent),'margin_per_game':sum(g['scored']-g['allowed'] for g in recent)/len(recent)})
   lifecycle_root=Path(source_root)/'public-lifecycle'/league
   initial=lifecycle_root/'initial-report.json'
   artifact_path=None
   if reports:
    report=json.loads(reports[0].read_text());artifact_path=artifacts/(report['id']+'.joblib')
   elif initial.exists():
    report=json.loads(initial.read_text());artifact_path=lifecycle_root/'initial.joblib'
   else:
    report=None
    if len(rows)>=700:
     try:
      report=train(isolated,temporary,league);lifecycle_root.mkdir(parents=True,exist_ok=True)
      artifact_path=lifecycle_root/'initial.joblib';shutil.copy2(Path(temporary)/'models'/(report['id']+'.joblib'),artifact_path)
      initial.write_text(json.dumps(report))
      with isolated:isolated.execute('DELETE FROM experiments WHERE league=?',(league,))
     except ValueError as e:item['limitation']=str(e)
   if report:
    item['benchmark']=report
    if not rows:item['limitation']='Historical benchmark is available, but current public results are unavailable.'
    else:
     lineage=json.loads((lifecycle_root/'state.json').read_text()) if (lifecycle_root/'state.json').exists() else {}
     benchmark_ids=set(lineage.get('benchmark_event_ids',[]))
     history=[r for r in rows if r['outcome'] in ('home','away') and (r['event_id'] in benchmark_ids if benchmark_ids else r['date']<=report['last_date'])]
     if version(history)!=report['dataset_sha256']:
      item['limitation']='Public history differs from the archived benchmark inputs; current forecasts are withheld for review.'
     elif not artifact_path.exists():item['limitation']='Selected model artifact unavailable.'
     else:
      model_dir=Path(temporary)/'models';model_dir.mkdir(exist_ok=True)
      champion,lifecycle=prepare(lifecycle_root,[r for r in rows if r['outcome'] in ('home','away')],report,artifact_path)
      import joblib
      joblib.dump(champion,model_dir/(report['id']+'.joblib'))
      item['lifecycle']=lifecycle
      with isolated:isolated.execute('INSERT INTO experiments VALUES(?,?,?,?)',(report['id'],league,report['created'],json.dumps(report)))
      item['model_refitted_at']=champion.get('refitted',report['created'])
      item['model_training_rows']=len(champion['training_event_ids'])
      item['model_training_sha256']=champion['digest']
      item['status']='historically backtested baseline'
      item['limitation']='Limited result-only model; important player and sport-specific inputs remain unconfirmed.'
      if not feed_fresh:item['limitation']='Current source feed unavailable or stale; no current forecasts. Archived backtest remains visible.'
      elif (today-date.fromisoformat(rows[-1]['date'])).days>30:item['limitation']='Results are over 30 days old; current forecasts withheld.'
      else:
       inputs=fixture_inputs([r for r in rows if r['outcome'] in ('home','away')],feed.get('upcoming',[]),champion['window'],champion['extra'])
       seen=set()
       for fixture in feed.get('upcoming',[]):
        safe={}
        try:
         identity=(fixture['date'],fixture['home'],fixture['away'])
         if identity in seen:continue
         seen.add(identity)
         scheduled=date.fromisoformat(fixture['date'])
         safe={'date':fixture['date'],'home':fixture['home'],'away':fixture['away']}
         event_start=parse_time(fixture['start_time']) if fixture.get('start_time') else None
         if event_start and event_start<=asof:
          item['withheld'].append(dict(safe,reason='Event start time has passed; pre-event forecast withheld.'));continue
         if scheduled<=today and event_start is None:
          item['withheld'].append(dict(safe,reason='Exact pregame start time is unverified; same-day/past forecasts withheld.'));continue
         if scheduled>today+timedelta(days=14):continue
         url=fixture.get('source','')
         if not fixture.get('confirmed_source') or urlparse(url).hostname not in {urlparse(FEEDS[league]['url']).hostname,*(['site.api.espn.com'] if league in ESPN_PATHS else []),*(['raw.githubusercontent.com'] if league in ('NBA','CFB') else [])}:
          item['withheld'].append(dict(safe,reason='Fixture source could not be verified.'));continue
         result=estimate(isolated,temporary,league,fixture['home'],fixture['away'],fixture['date'],allow_updated_history=True,neutral=fixture.get('neutral')=='1',prepared_inputs=inputs)
         result.update(id=str(fixture.get('id','-'.join(identity))),mode='limited pre-event model forecast',generated_at=asof.isoformat(),valid_until=min(parse_time(feed['checked'])+timedelta(hours=24),event_start or datetime.combine(scheduled,datetime.min.time(),timezone.utc),asof+timedelta(hours=24)).isoformat(),event_start_utc=event_start.isoformat() if event_start else None,schedule_source=url,schedule_checked=feed['checked'],availability='Schedule date from public source; injuries, starters, pitchers, goalies and lineups unconfirmed.')
         item['predictions'].append(result)
        except (ValueError,KeyError,TypeError) as e:
         item['withheld'].append(dict(safe,reason=str(e)))
       item['predictions'].sort(key=lambda p:max(p['home_probability'],p['away_probability']),reverse=True)
   if item['lifecycle']:record(lifecycle_root,item['predictions'])
   snapshot['leagues'].append(item)
  # Estimating public forecasts must never write to either prediction ledger.
  assert isolated.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]==0
  isolated.close()
 source.close()
 return snapshot

def write_site(snapshot,destination,project):
 destination=Path(destination);project=Path(project)
 if destination.exists() and destination.resolve()!=project.resolve():
  allowed={'index.html','.nojekyll','web','web/app.js','web/style.css','web/icon.svg','web/data','web/data/snapshot.json'}
  for existing in destination.rglob('*'):
   if existing.is_symlink() or str(existing.relative_to(destination)) not in allowed:
    raise ValueError('Output contains unexpected files; use a clean public build directory')
 destination.mkdir(parents=True,exist_ok=True)
 if destination.resolve()!=project.resolve():
  shutil.copy2(project/'index.html',destination/'index.html')
  assets=destination/'web';assets.mkdir(exist_ok=True)
  for name in ('app.js','style.css','icon.svg'):shutil.copy2(project/'web'/name,assets/name)
 (destination/'.nojekyll').write_text('')
 data=destination/'web'/'data';data.mkdir(parents=True,exist_ok=True)
 (data/'snapshot.json').write_text(json.dumps(snapshot,allow_nan=False,separators=(',',':'))+'\n')
