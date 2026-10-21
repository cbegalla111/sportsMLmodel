from datetime import date
from sportslab.refresh import espn_events

def test_scoreboard_ignores_market_fields_and_incomplete_games():
 c=lambda side,score:{'id':side,'homeAway':side,'team':{'displayName':side},'score':score,'odds':{'spread':5}}
 final={'id':'game','date':'2020-01-01T20:00Z','status':{'type':{'completed':True}},'competitors':[c('home','100'),c('away','90')],'odds':[{'spread':5}]}
 pending=dict(final,id='future',date='2020-01-03T20:00Z',status={'type':{'state':'pre'}})
 rows,fixtures=espn_events({'events':[{'competitions':[final,pending]}]},'WNBA','https://site.api.espn.com',date(2020,1,2))
 assert len(rows)==1 and rows[0]['outcome']=='home'
 assert not any('odds' in key for key in rows[0])
 assert fixtures[0]['id']=='espn-wnba-future'

def test_ufc_winner_flags_not_fake_score_inference():
 bout={'id':'bout','date':'2020-01-01T20:00Z','status':{'type':{'completed':True}},'competitors':[{'id':'2','athlete':{'displayName':'B'},'winner':True},{'id':'1','athlete':{'displayName':'A'},'winner':False}]}
 rows,_=espn_events({'events':[{'competitions':[bout]}]},'UFC','https://site.api.espn.com',date(2020,1,2))
 assert rows[0]['home']=='A' and rows[0]['outcome']=='away' and rows[0]['neutral']=='1'
 for c in bout['competitors']:c['winner']=False
 rows,_=espn_events({'events':[{'competitions':[bout]}]},'UFC','https://site.api.espn.com',date(2020,1,2))
 assert rows[0]['outcome']=='no_contest'
