from datetime import datetime,timezone,timedelta
import json
from sportslab.grading import ResultIndex,combine
from sportslab.pages import prediction_history
from sportslab.results import espn_competition,refresh,load

def pick(id='espn-nba-100'):
 return {'id':id,'date':'2026-10-29','home':'A','away':'B','home_probability':.7,'generated_at':'2026-10-29T12:00:00+00:00','model':'model','dataset_sha256':'unchanged','prediction_policy':'policy'}
def result(id='espn-nba-100'):
 return {'event_id':id,'date':'2026-10-30','home':'A','away':'B','home_score':110,'away_score':100,'outcome':'home'}

def test_id_matches_utc_date_difference_and_not_wrong_doubleheader():
 r=result();assert ResultIndex([r]).find(pick())==r
 assert ResultIndex([result('mlb-101')]).find(dict(pick('100'),date='2026-10-30')) is None
 assert ResultIndex([r]).find(dict(pick(),home='Other')) is None
 assert ResultIndex([r,dict(r,outcome='away')]).find(pick()) is None
 assert ResultIndex([r,dict(r,home_score='110.0',away_score='100.0')]).find(pick()) is not None

def test_ufc_orientation_is_mapped_and_hockey_names_match_codes():
 p=pick('espn-ufc-100');r=dict(result('espn-ufc-100'),home='B',away='A')
 matched=ResultIndex([r]).find(p);assert matched['outcome']=='away' and matched['home_score']==100
 p=dict(pick('100'),home='Seattle Kraken',away='Calgary Flames');r=dict(result('nhl-100'),home='SEA',away='CGY');assert ResultIndex([r]).find(p)==r

def test_history_uses_verified_start_and_keeps_probability_immutable(tmp_path):
 p=pick();(tmp_path/'state.json').write_text(json.dumps({'ledger':{'first':p}}));r=result()
 statuses=[dict(r,start_time='2026-10-30T00:00:00Z',state='final',checked='2026-10-31T00:00:00Z')]
 rows=prediction_history(tmp_path,[r],datetime(2026,10,31,tzinfo=timezone.utc),statuses)
 assert rows[0]['correct'] is True and rows[0]['home_probability']==.7
 assert rows[0]['event_start_utc'].startswith('2026-10-30')
 assert json.loads((tmp_path/'state.json').read_text())['ledger']['first']==p
 # Corrected source times can expose a prediction made after the actual start.
 p['generated_at']='2026-10-30T01:00:00Z';p['event_start_utc']='2026-10-30T02:00Z';(tmp_path/'state.json').write_text(json.dumps({'ledger':{'first':p}}))
 row=prediction_history(tmp_path,[r],datetime(2026,10,31,tzinfo=timezone.utc),statuses)[0]
 assert row['correct'] is None and row['result_status']=='not_pregame'

def test_future_legacy_version_is_not_counted_pending(tmp_path):
 p=pick();p['date']='2026-10-30';(tmp_path/'state.json').write_text(json.dumps({'ledger':{'first':p},'policy_ledgers':{'new':{'first':dict(p,event_start_utc='2026-10-30T23:00Z')}}}))
 assert prediction_history(tmp_path,[],datetime(2026,10,30,12,tzinfo=timezone.utc))==[]

def test_source_final_requires_identity_and_status():
 p=dict(pick(),league='NBA')
 c={'id':'100','date':'2026-10-30T00:00Z','status':{'type':{'completed':True,'state':'post'}},'competitors':[{'homeAway':'home','team':{'displayName':'A'},'score':'110'},{'homeAway':'away','team':{'displayName':'B'},'score':'100'}]}
 r=espn_competition(c,p,'https://source.example');assert r['outcome']=='home'
 c['status']={'type':{'state':'pre'}};r=espn_competition(c,p,'https://source.example');assert r['outcome'] is None and r['state']=='scheduled'


def test_result_refresh_preserves_verified_final_when_source_fails(tmp_path):
 p=dict(pick(),event_start_utc='2026-10-30T00:00Z');root=tmp_path/'public-lifecycle/NBA';root.mkdir(parents=True);(root/'state.json').write_text(json.dumps({'ledger':{'one':p}}))
 c={'id':'100','date':'2026-10-30T00:00Z','status':{'type':{'completed':True}},'competitors':[{'homeAway':'home','team':{'displayName':'A'},'score':'110'},{'homeAway':'away','team':{'displayName':'B'},'score':'100'}]}
 now=datetime(2026,10,31,tzinfo=timezone.utc);refresh(tmp_path,now,lambda u:{'header':{'competitions':[c]}})
 before=load(tmp_path)['events']['NBA:100']
 def offline(u):raise OSError('offline')
 refresh(tmp_path,now+timedelta(days=1),offline)
 assert load(tmp_path)['events']['NBA:100']==before
 assert len(combine([result()], [dict(result(),home_score=111)]))==1
