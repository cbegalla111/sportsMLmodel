import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LEAGUES = ('NBA','NFL','NHL','CFB','WNBA','MLB','UFC')
FEATURES = {
 'NBA': ['offensive_rating','defensive_rating','pace','efg','turnover_rate','rebound_rate'],
 'WNBA': ['offensive_rating','defensive_rating','pace','efg','turnover_rate','rebound_rate'],
 'NFL': ['epa','success_rate','qb_rating'], 'CFB': ['epa','success_rate','schedule_strength'],
 'MLB': ['starter_k_rate','starter_bb_rate','batting_ops','bullpen_era'],
 'NHL': ['xg_share','power_play_rate','penalty_kill_rate','goalie_save_rate'],
 'UFC': ['strikes_per_min','strike_defense','takedown_rate','takedown_defense','age','reach','layoff_days']}
BASE = ['event_id','league','date','home','away','home_score','away_score','outcome','source','neutral']
EXTRA = ['feature_asof'] + sorted({side+'_'+f for fs in FEATURES.values() for f in fs for side in ('home','away')})
FORBIDDEN = ('odds','spread','moneyline','implied','market','elo','forecast','probability')

def now(): return datetime.now(timezone.utc).isoformat()

def connect(root):
 root = Path(root); root.mkdir(parents=True, exist_ok=True)
 db = sqlite3.connect(root/'lab.sqlite3'); db.row_factory = sqlite3.Row
 db.executescript('''PRAGMA journal_mode=WAL;
 CREATE TABLE IF NOT EXISTS games(event_id TEXT PRIMARY KEY, league TEXT, date TEXT, payload TEXT);
 CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY, league TEXT, created TEXT, payload TEXT);
 CREATE TABLE IF NOT EXISTS predictions(id INTEGER PRIMARY KEY, created TEXT, payload TEXT);
 CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
 ''')
 return db

def validate(rows):
 clean=[]; seen=set()
 for i,r in enumerate(rows,2):
  unknown=set(r)-set(BASE+EXTRA)
  if unknown: raise ValueError(f'Row {i}: unsupported columns {sorted(unknown)}. Market inputs are prohibited.')
  if any(any(w in k.lower() for w in FORBIDDEN) for k in r): raise ValueError('Market/derived prediction columns prohibited')
  r={k:str(v).strip() for k,v in r.items() if v is not None and str(v).strip()}
  for k in BASE:
   if k not in r: raise ValueError(f'Row {i}: missing {k}')
  if r['league'] not in LEAGUES: raise ValueError('Unsupported league')
  datetime.strptime(r['date'],'%Y-%m-%d')
  if r['date']>datetime.now(timezone.utc).date().isoformat(): raise ValueError('Historical results cannot be dated in the future')
  if len(r['date']) != 10: raise ValueError('Use ISO dates')
  if not r['home'] or r['home']==r['away']: raise ValueError('Two different opponents required')
  if r['event_id'] in seen: raise ValueError('Duplicate event_id in upload')
  seen.add(r['event_id'])
  if r['neutral'] not in ('0','1'): raise ValueError('neutral must be 0 or 1')
  hs,aws=float(r['home_score']),float(r['away_score'])
  import math
  if not all(math.isfinite(v) and v>=0 for v in (hs,aws)): raise ValueError('Scores must be finite and nonnegative')
  if r['outcome'] not in ('home','away','draw','no_contest'): raise ValueError('Invalid outcome')
  if r['outcome'] in ('home','away') and ((hs<=aws if r['outcome']=='home' else aws<=hs)) and r['league']!='UFC': raise ValueError('Outcome disagrees with score')
  if r['outcome']=='draw' and hs!=aws: raise ValueError('Draw must have equal scores')
  if r['outcome'] in ('draw','no_contest') and r['league'] not in ('NFL','CFB','UFC'): raise ValueError('This league requires eventual winner scores, including overtime/shootouts')
  allowed={s+'_'+f for f in FEATURES[r['league']] for s in ('home','away')}
  supplied=set(r)-set(BASE)-{'feature_asof'}
  if supplied-allowed: raise ValueError('Feature does not belong to selected sport')
  if supplied:
   if not r.get('feature_asof'): raise ValueError('Pregame features require feature_asof strictly before event date (UTC)')
   stamp=datetime.fromisoformat(r['feature_asof'].replace('Z','+00:00'))
   boundary=datetime.strptime(r['date'],'%Y-%m-%d').replace(tzinfo=timezone.utc)
   if stamp.tzinfo is None or stamp.astimezone(timezone.utc)>=boundary: raise ValueError('Pregame features require a timezone and feature_asof strictly before event date (UTC)')
   for k in supplied:
    if not math.isfinite(float(r[k])): raise ValueError('Nonfinite feature')
  clean.append(r)
 if not clean: raise ValueError('No rows')
 return clean

def ingest(db, rows):
 rows=validate(rows)
 for r in rows:
  existing=db.execute('SELECT payload FROM games WHERE event_id=?',(r['event_id'],)).fetchone()
  if existing and json.loads(existing[0])!=r: raise ValueError('Conflicting event_id; existing history is immutable')
 with db:
  db.executemany('INSERT OR IGNORE INTO games VALUES(?,?,?,?)',[(r['event_id'],r['league'],r['date'],json.dumps(r,sort_keys=True)) for r in rows])
 return len(rows)

def load(db,league):
 return [json.loads(x[0]) for x in db.execute('SELECT payload FROM games WHERE league=? ORDER BY date,event_id',(league,))]

def version(rows): return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()

def parse_csv(text): return list(csv.DictReader(io.StringIO(text)))
