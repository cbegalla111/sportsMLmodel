"""Synthetic box scores; no fixture outcomes are published."""
from datetime import datetime,timezone
import json
from sportslab.props import parse_box,refresh,load_public

EVENT={'id':'test-game','date':'2026-11-01T19:00Z'}
def box(keys,stats,group='athletes',dnp=False,completed=True):
 return {'header':{'competitions':[{'status':{'type':{'completed':completed}}}]},'boxscore':{'players':[{'team':{'displayName':'Synthetic team'},'statistics':[{'name':group,'keys':keys,'athletes':[{'athlete':{'id':'1','displayName':'Synthetic player'},'stats':stats,'didNotPlay':dnp}]}]}]}}

def test_basketball_makes_and_combinations_exclude_dnp_and_nonfinal():
 payload=box(['points','rebounds','assists','threePointFieldGoalsMade-threePointFieldGoalsAttempted'],['20','4','6','3-8'])
 rows=parse_box(payload,'NBA',EVENT)
 assert rows[0]['values']=={'Points':20,'Rebounds':4,'Assists':6,'Threes made':3,'Points + rebounds + assists':30}
 assert not parse_box(box(['points'],['20'],dnp=True),'NBA',EVENT)
 assert not parse_box(box(['points'],['20'],completed=False),'NBA',EVENT)
 assert not parse_box(box(['points'],['nan']),'NBA',EVENT)

def test_baseball_batter_strikeouts_not_pitcher_props():
 assert parse_box(box(['hits','strikeouts'],['2','3'],'batting'),'MLB',EVENT)[0]['values']=={'Hits':2}
 assert parse_box(box(['hits','strikeouts'],['6','7'],'pitching'),'MLB',EVENT)[0]['values']=={'Pitcher strikeouts':7}

def test_nfl_groups_merge_and_hockey_duplicates_deduplicate():
 p=box(['rushingYards'],['45'],'rushing');g=box(['receptions'],['4'],'receiving')['boxscore']['players'][0]['statistics'][0]
 p['boxscore']['players'][0]['statistics'].append(g)
 assert parse_box(p,'NFL',EVENT)[0]['values']=={'Rushing yards':45,'Receptions':4}
 p=box(['shotsTotal'],['4'],'forwards');p['boxscore']['players'][0]['statistics']*=2
 assert len(parse_box(p,'NHL',EVENT))==1

def test_refresh_reuses_verified_games_preserves_on_failure_and_excludes_future(tmp_path):
 asof=datetime(2026,11,2,tzinfo=timezone.utc)
 e=dict(EVENT,status={'type':{'completed':True}})
 def source(url):
  if '/summary?' in url:return box(['points'],['20'])
  return {'events':[e,dict(e,id='future',date='2027-01-01T19:00Z')]}
 refresh(tmp_path,asof,source,cap=2)
 data=load_public(tmp_path)
 assert data['leagues']['NBA']['games']==1
 assert len(data['leagues']['NBA']['players'][0]['games'])==1
 assert data['leagues']['NBA']['players'][0]['games'][0]['event_id']=='test-game'
 def offline(url):raise OSError('offline')
 refresh(tmp_path,asof,offline,cap=2)
 data=load_public(tmp_path)
 assert data['leagues']['NBA']['error']
 assert data['leagues']['NBA']['games']==1
 json.dumps(data,allow_nan=False)

def test_corrupt_optional_snapshot_does_not_break_team_dashboard(tmp_path):
 directory=tmp_path/'public-props';directory.mkdir();(directory/'snapshot.json').write_text('broken')
 assert load_public(tmp_path)['leagues']=={}

def test_negative_football_yardage_is_a_valid_observation():
 rows=parse_box(box(['rushingYards','receptions'],['-3','-1'],'rushing'),'NFL',EVENT)
 assert rows[0]['values']=={'Rushing yards':-3}
