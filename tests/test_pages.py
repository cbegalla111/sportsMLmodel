"""Synthetic fixtures only; these tests never create the website's published data."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import joblib
import pytest
from sportslab.data import connect,ingest,version
from sportslab.pages import export_snapshot,PUBLIC_SOURCES
from sportslab.refresh import FEEDS

@pytest.fixture
def public_source(tmp_path):
 root=tmp_path/'private';artifacts=tmp_path/'public-artifacts';artifacts.mkdir();db=connect(root)
 now=datetime.now(timezone.utc);rows=[]
 for i in range(120):
  rows.append({'event_id':'nflverse-test-'+str(i),'league':'NFL','date':(now.date()-timedelta(days=120-i)).isoformat(),'home':'Synthetic A' if i%2 else 'Synthetic B','away':'Synthetic B' if i%2 else 'Synthetic A','home_score':'21','away_score':'14','outcome':'home','neutral':'0','source':PUBLIC_SOURCES['NFL'][1]})
 ingest(db,rows)
 private=dict(rows[0],event_id='private-csv',source='PRIVATE_UPLOAD_SENTINEL',home='PRIVATE_TEAM_SENTINEL');ingest(db,[private])
 with db:db.execute('INSERT INTO predictions(created,payload) VALUES(?,?)',(now.isoformat(),json.dumps({'note':'PRIVATE_HISTORY_SENTINEL'})))
 (root/'auth.json').write_text('PRIVATE_CREDENTIAL_SENTINEL')
 (root/'models').mkdir();(root/'models'/'NFL-test.joblib').write_text('Private model must not be loaded')
 report={'id':'NFL-test','league':'NFL','created':now.isoformat(),'dataset_sha256':version(rows),'n_rows':120,'first_date':rows[0]['date'],'last_date':rows[-1]['date'],'selected':'elo_w20','outcome_rules':'Synthetic test-only decisive outcomes'}
 (artifacts/'NFL-test.json').write_text(json.dumps(report));joblib.dump({'model':None,'window':20,'extra':False,'names':['elo_difference','home_advantage','win_rate_difference','scoring_margin_difference','rest_difference'],'digest':version(rows),'last_date':rows[-1]['date'],'league':'NFL','neutral_variation':False},artifacts/'NFL-test.joblib')
 fixture={'id':'synthetic-future','date':(now.date()+timedelta(days=1)).isoformat(),'home':'Synthetic A','away':'Synthetic B','confirmed_source':True,'source':FEEDS['NFL']['url']}
 feed={'status':'ok','checked':now.isoformat(),'upcoming':[fixture,fixture]}
 with db:db.execute('INSERT INTO settings VALUES(?,?)',('feed_NFL',json.dumps(feed)))
 yield root,artifacts,db,feed,now
 db.close()

def test_public_export_excludes_private_data_and_does_not_touch_history(public_source):
 root,artifacts,db,feed,now=public_source
 snapshot=export_snapshot(root,artifacts,now);text=json.dumps(snapshot)
 assert 'PRIVATE_' not in text
 assert len(snapshot['leagues'])==7
 nfl=next(x for x in snapshot['leagues'] if x['name']=='NFL')
 assert nfl['result_count']==120 and len(nfl['predictions'])==1
 p=nfl['predictions'][0];assert p['home_probability']+p['away_probability']==pytest.approx(1)
 assert p['mode']=='limited pre-event model forecast' and p['generated_at']==now.isoformat()
 assert datetime.fromisoformat(p['valid_until'])<=now+timedelta(hours=24)
 assert db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]==1
 assert len(nfl['teams'])==2

def test_stale_source_preserves_benchmark_but_withholds_forecasts(public_source):
 root,artifacts,db,feed,now=public_source;feed['checked']=(now-timedelta(days=2)).isoformat()
 with db:db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(feed),'feed_NFL'))
 nfl=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert nfl['benchmark'] and not nfl['predictions'] and nfl['feed_status']=='stale'

def test_same_day_and_unverified_sources_are_withheld(public_source):
 root,artifacts,db,feed,now=public_source
 fixture=feed['upcoming'][0];today=dict(fixture,id='synthetic-today',date=now.date().isoformat());unverified=dict(fixture,id='synthetic-unverified',home='Synthetic B',away='Synthetic A',source='https://unverified.example/schedule')
 feed['upcoming']=[today,unverified]
 with db:db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(feed),'feed_NFL'))
 nfl=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert not nfl['predictions'] and len(nfl['withheld'])==2
 assert 'start time' in nfl['withheld'][0]['reason'] and 'verified' in nfl['withheld'][1]['reason']

def test_changed_archived_history_cannot_claim_original_validation(public_source):
 root,artifacts,db,feed,now=public_source
 report=json.loads((artifacts/'NFL-test.json').read_text());report['dataset_sha256']='mismatched';(artifacts/'NFL-test.json').write_text(json.dumps(report))
 nfl=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert nfl['benchmark'] and not nfl['predictions'] and 'differs' in nfl['limitation']

def test_verified_same_day_start_allows_only_pre_event_forecast(public_source):
 root,artifacts,db,feed,now=public_source
 fixture=dict(feed['upcoming'][0],date=now.date().isoformat(),start_time=(now+timedelta(hours=2)).isoformat())
 feed['upcoming']=[fixture]
 with db:db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(feed),'feed_NFL'))
 nfl=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert len(nfl['predictions'])==1
 assert nfl['predictions'][0]['valid_until']==fixture['start_time']
 fixture['start_time']=(now-timedelta(minutes=1)).isoformat()
 with db:db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(feed),'feed_NFL'))
 nfl=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert not nfl['predictions'] and 'passed' in nfl['withheld'][0]['reason']

def test_static_publish_directory_cannot_include_stray_private_files(tmp_path):
 from sportslab.pages import write_site
 output=tmp_path/'site';output.mkdir();(output/'auth.json').write_text('PRIVATE_SENTINEL')
 with pytest.raises(ValueError,match='unexpected files'):write_site({'leagues':[]},output,Path.cwd())
 assert (output/'auth.json').read_text()=='PRIVATE_SENTINEL'

def test_backfill_preserves_verified_training_subset_and_original_benchmark(public_source):
 root,artifacts,db,feed,now=public_source
 before=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 row=json.loads(db.execute("SELECT payload FROM games WHERE event_id='nflverse-test-0'").fetchone()[0]);row['event_id']='nflverse-added-historical-game';ingest(db,[row])
 after=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert after['result_count']==before['result_count']+1
 assert after['benchmark']==before['benchmark']
 assert after['model_training_sha256']==before['model_training_sha256']
 assert after['model_training_rows']==before['model_training_rows']
 assert after['predictions']
 assert after['predictions'][0]['input_dataset_sha256']!=before['predictions'][0]['input_dataset_sha256']
 # An actual revision of an observation used in training still invalidates lineage.
 row=json.loads(db.execute("SELECT payload FROM games WHERE event_id='nflverse-test-1'").fetchone()[0]);row['home_score']='22'
 with db:db.execute('UPDATE games SET payload=? WHERE event_id=?',(json.dumps(row),row['event_id']))
 invalid=next(x for x in export_snapshot(root,artifacts,now)['leagues'] if x['name']=='NFL')
 assert not invalid['predictions'] and 'differs' in invalid['limitation']


def test_distinct_same_day_matchups_are_not_collapsed(public_source):
 root,artifacts,db,feed,now=public_source
 first=feed['upcoming'][0];feed['upcoming']=[first,dict(first,id='second-game')]
 with db:db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(feed),'feed_NFL'))
 item=next(l for l in export_snapshot(root,artifacts,now)['leagues'] if l['name']=='NFL')
 assert {p['id'] for p in item['predictions']}=={first['id'],'second-game'}
