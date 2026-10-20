import json
import pytest
from sportslab.data import connect, ingest, load, validate

def result(**kw):
 return dict(event_id='real-input-test-only',league='NBA',date='2020-01-01',home='Test A',away='Test B',home_score='100',away_score='90',outcome='home',source='synthetic unit test fixture; not real data',neutral='0',**kw)

def test_persistence_and_immutable_ids(tmp_path):
 db=connect(tmp_path); ingest(db,[result()]); ingest(db,[result()]); db.close()
 db=connect(tmp_path); assert len(load(db,'NBA'))==1
 changed=result(); changed['home_score']='101'
 with pytest.raises(ValueError,match='Conflicting'): ingest(db,[changed])
 assert load(db,'NBA')[0]['home_score']=='100'

def test_batch_is_atomic(tmp_path):
 db=connect(tmp_path); ingest(db,[result()]); other=result();other['event_id']='new'
 conflict=result();conflict['home_score']='101'
 with pytest.raises(ValueError): ingest(db,[other,conflict])
 assert len(load(db,'NBA'))==1

@pytest.mark.parametrize('change',[{'home_odds':'-110'},{'home_score':'nan'},{'home_score':'-1'},{'away':'Test A'},{'date':'2099-01-01'},{'outcome':'away'},{'league':'SOCCER'},{'neutral':'2'},{'elo':'1500'},{'outcome':'draw'}])
def test_invalid_inputs(change):
 r=result();r.update(change)
 with pytest.raises(ValueError): validate([r])

def test_feature_timestamps():
 r=result();r.update(home_pace='100',feature_asof='2020-01-01T00:00:00Z')
 with pytest.raises(ValueError,match='strictly before'): validate([r])
 r['feature_asof']='2019-12-31T23:00:00Z';assert validate([r])
 r['feature_asof']='2019-12-31T23:00:00-12:00'
 with pytest.raises(ValueError,match='strictly before'):validate([r])
 r['feature_asof']='2019-12-31T23:00:00Z'
 r['home_pace']='nan'
 with pytest.raises(ValueError):validate([r])

def test_ties_and_ufc_rules():
 for league in ('NFL','UFC'):
  r=result();r.update(league=league,home_score='0',away_score='0',outcome='draw');assert validate([r])
 r['outcome']='no_contest';assert validate([r])
