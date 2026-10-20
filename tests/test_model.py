import copy
from datetime import date,timedelta
import json
import numpy as np
import pytest
from sportslab.data import connect, ingest, load
from sportslab.model import features, train, predict, refit_frozen, evaluate

def synthetic_rows(n=800):
 # Clearly synthetic only for test coverage. Never loaded into the application database.
 rng=np.random.default_rng(42);rows=[]
 for i in range(n):
  h='T'+str(i%8);a='T'+str((i+1+i//8)%8)
  if h==a:a='T'+str((int(a[1:])+1)%8)
  hs=int(rng.integers(80,130));aws=int(rng.integers(80,130));aws=aws if aws!=hs else aws+1
  rows.append(dict(event_id=str(i),league='NBA',date=(date(2010,1,1)+timedelta(days=i//4)).isoformat(),home=h,away=a,home_score=str(hs),away_score=str(aws),outcome='home' if hs>aws else 'away',source='synthetic test only',neutral='0'))
 return rows

def test_no_current_game_or_same_day_leakage():
 rows=synthetic_rows(80);original,_=features(rows)
 changed=copy.deepcopy(rows);day=changed[40]['date']
 for r in changed:
  if r['date']>=day:r.update(home_score='500',away_score='0',outcome='home')
 mutated,_=features(changed)
 for a,b in zip(original,mutated):
  if a[0]['date']<=day: assert a[1]==b[1]
 assert any(a[1]!=b[1] for a,b in zip(original,mutated) if a[0]['date']>day)

def test_expanding_validation_persistence_probability_and_staleness(tmp_path):
 db=connect(tmp_path);ingest(db,synthetic_rows());r=train(db,tmp_path,'NBA')
 for c in r['candidates']:
  if c['status']=='completed':
   for f in c['folds']:assert f['train_end']<f['validation_start']<=f['validation_end']<r['final_test_start']
 assert r['test']['n']>0 and r['test']['n']<r['n_rows'];assert sum(b['n'] for b in r['test']['calibration'])==r['test']['n']
 assert train(db,tmp_path,'NBA')==r
 p=predict(db,tmp_path,'NBA','T0','T1','2010-07-20',True)
 assert p['home_probability']+p['away_probability']==pytest.approx(1)
 assert p['mode']=='hypothetical scenario'
 with pytest.raises(ValueError,match='stale'):predict(db,tmp_path,'NBA','T0','T1',date.today().isoformat(),False)
 with pytest.raises(ValueError,match='follow'):predict(db,tmp_path,'NBA','T0','T1','2010-01-02',True)
 with pytest.raises(ValueError):predict(db,tmp_path,'NBA','T0','T1','2010-07-20',True,{'neutral':float('nan')})
 with pytest.raises(ValueError):predict(db,tmp_path,'NBA','T0','T1','2010-07-20',True,{'home_pace':120})
 db.close();db=connect(tmp_path);assert db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]==1
 # New observations do not reopen the selection/final test.
 new=synthetic_rows(804)[-4:];ingest(db,new)
 with pytest.raises(ValueError,match='sealed'):train(db,tmp_path,'NBA')
 assert refit_frozen(db,tmp_path,'NBA')=='refitted frozen specification'
 p=predict(db,tmp_path,'NBA','T0','T1','2010-07-21',True)
 assert p['home_probability']+p['away_probability']==pytest.approx(1)
 assert json.loads(db.execute('SELECT payload FROM experiments').fetchone()[0])==r

def test_withhold_small_dataset(tmp_path):
 db=connect(tmp_path);ingest(db,synthetic_rows(100))
 with pytest.raises(ValueError,match='700'):train(db,tmp_path,'NBA')
