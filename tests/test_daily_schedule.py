from datetime import date
from sportslab.refresh import daily_events

def event(identity,start,state,completed=False):
 return {'date':start,'competitions':[{'id':identity,'date':start,'status':{'type':{'state':state,'completed':completed,'description':state}},'competitors':[{'homeAway':'home','team':{'displayName':'A'}},{'homeAway':'away','team':{'displayName':'B'}}]}]}

def test_all_states_including_late_utc_events_are_retained_on_eastern_day():
 payload={'events':[event('pre','2026-11-08T22:00:00Z','pre'),event('live','2026-11-08T18:00:00Z','in'),event('final','2026-11-08T17:00:00Z','post',True),event('late','2026-11-09T02:00:00Z','pre'),event('previous','2026-11-08T02:00:00Z','post',True)]}
 rows=daily_events(payload,'NBA',date(2026,11,8))
 assert len(rows)==4
 assert {r['state'] for r in rows}=={'pre','in','post'}
 assert all(r['date']=='2026-11-08' for r in rows)
 assert any(r['id']=='espn-nba-late' for r in rows)
 assert next(r for r in rows if r['id']=='espn-nba-final')['completed']

def test_daily_events_deduplicate_and_skip_unknown_opponents_or_bad_times():
 good=event('one','2026-11-08T22:00:00Z','in');bad=event('bad','no time','pre')
 assert len(daily_events({'events':[good,good,bad]},'NBA',date(2026,11,8)))==1


def test_daily_refresh_queries_individual_dates_and_persists_all_states(tmp_path,monkeypatch):
 import json
 from datetime import datetime,timezone
 from sportslab.refresh import refresh_daily_schedules
 from sportslab.data import connect
 calls=[]
 def fake(root,url,league):
  calls.append((url,league));payload={'events':[event('live','2026-11-08T18:00:00Z','in'),event('final','2026-11-08T17:00:00Z','post',True)]}
  if league=='UFC':
   for e in payload['events']:
    for i,c in enumerate(e['competitions'][0]['competitors']):c.update(id=str(i),athlete=c['team'])
  return json.dumps(payload).encode(),{}
 monkeypatch.setattr('sportslab.refresh.fetch',fake)
 reports=refresh_daily_schedules(tmp_path,datetime(2026,11,8,23,tzinfo=timezone.utc))
 assert len(reports)==7 and all(r['status']=='ok' and r['events']==2 for r in reports)
 assert len(calls)==14
 assert all('dates=20261108&' in u or 'dates=20261109&' in u for u,l in calls)
 assert all('groups=80' in u for u,l in calls if l=='CFB')
 with connect(tmp_path) as db:
  value=json.loads(db.execute("select value from settings where key='daily_schedule_NBA'").fetchone()[0])
 assert value['day']=='2026-11-08' and len(value['events'])==2
