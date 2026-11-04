"""Match verified results to immutable forecasts by event identity before dates."""
from datetime import date
import re
import unicodedata

PREFIXES=('espn-nba-','espn-nfl-','espn-nhl-','espn-cfb-','espn-wnba-','espn-ufc-','nflverse-','mlb-','nhl-','nba-cdn-')
NHL={'Seattle Kraken':'SEA','Calgary Flames':'CGY','Los Angeles Kings':'LAK','San Jose Sharks':'SJS','Anaheim Ducks':'ANA','Boston Bruins':'BOS','Buffalo Sabres':'BUF','Carolina Hurricanes':'CAR','Chicago Blackhawks':'CHI','Colorado Avalanche':'COL','Columbus Blue Jackets':'CBJ','Dallas Stars':'DAL','Detroit Red Wings':'DET','Edmonton Oilers':'EDM','Florida Panthers':'FLA','Minnesota Wild':'MIN','Montréal Canadiens':'MTL','Montreal Canadiens':'MTL','Nashville Predators':'NSH','New Jersey Devils':'NJD','New York Islanders':'NYI','New York Rangers':'NYR','Ottawa Senators':'OTT','Philadelphia Flyers':'PHI','Pittsburgh Penguins':'PIT','St. Louis Blues':'STL','Tampa Bay Lightning':'TBL','Toronto Maple Leafs':'TOR','Utah Mammoth':'UTA','Vancouver Canucks':'VAN','Vegas Golden Knights':'VGK','Washington Capitals':'WSH','Winnipeg Jets':'WPG'}

def identity(value):
 value=str(value)
 for prefix in PREFIXES:
  if value.startswith(prefix):return value[len(prefix):]
 return value

def team(value):
 value=NHL.get(str(value),str(value));value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode()
 return re.sub(r'[^a-z0-9]','',value.lower().replace('la clippers','los angeles clippers'))

def align(entry,result):
 h,a=team(entry['home']),team(entry['away']);rh,ra=team(result['home']),team(result['away'])
 if (h,a)==(rh,ra):return result
 if str(entry['id']).startswith('espn-ufc-') and (h,a)==(ra,rh):
  return dict(result,home=entry['home'],away=entry['away'],home_score=result.get('away_score'),away_score=result.get('home_score'),outcome={'home':'away','away':'home'}.get(result.get('outcome'),result.get('outcome')))
 return None

class ResultIndex:
 def __init__(self,rows):
  self.by_id={};self.by_match={}
  for r in rows:
   self.by_id.setdefault(identity(r['event_id']),[]).append(r)
   self.by_match.setdefault((r['date'],team(r['home']),team(r['away'])),[]).append(r)
 def find(self,entry):
  exact=self.by_id.get(identity(entry['id']),[])
  matches=[r for r in (align(entry,r) for r in exact) if r]
  if matches:
   outcomes={(r['outcome'],float(r['home_score']) if r.get('home_score') is not None else None,float(r['away_score']) if r.get('away_score') is not None else None) for r in matches}
   return matches[-1] if len(outcomes)==1 else None
  # A known provider ID must never fall back to another doubleheader's result.
  stable=any(str(entry['id']).startswith(p) for p in PREFIXES) or str(entry['id']).isdigit() or bool(re.fullmatch(r'\d{4}_\d{2}_[A-Z]+_[A-Z]+',str(entry['id'])))
  if exact or stable:return None
  matches=self.by_match.get((entry['date'],team(entry['home']),team(entry['away'])),[])
  return matches[0] if len(matches)==1 else None

def combine(rows,verified):
 """Only the separately verified exact-event feed overrides a stale result mirror."""
 overrides={identity(r['event_id']) for r in verified}
 return [r for r in rows if identity(r['event_id']) not in overrides]+list(verified)
