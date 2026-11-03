from datetime import date,timedelta
import json
import pytest
from sportslab.diagnostics import analyze

def records(n=100):
 return [{'id':str(i),'date':(date(2020,1,1)+timedelta(days=i)).isoformat(),'home':'A','away':'B','home_probability':.9,'settled':True,'outcome':'home' if i%2==0 else 'away'} for i in range(n)]

def test_saved_predictions_only_and_calibration_gap():
 rows=records();rows.append(dict(rows[0],id='unsettled',settled=False));rows.append(dict(rows[0],id='draw',outcome='draw'))
 r=analyze(rows)
 assert r['n']==100 and r['rolling'][-1]['accuracy']==.5
 assert r['rolling'][-1]['confidence_gap']==pytest.approx(.4)
 assert r['rolling'][-1]['high_confidence_misses']==50
 assert r['calibration']['expected_calibration_error']==pytest.approx(.4)
 assert len(r['teams'])==2 and len(r['venues'])==1
 json.dumps(r,allow_nan=False)

def test_drift_requires_sample_and_does_not_invent_a_cause():
 assert analyze([])['n']==0
 assert analyze(records(20))['drift']['status']=='insufficient evidence'
 rows=records()
 for i,r in enumerate(rows):r['outcome']='home' if i<50 else 'away'
 r=analyze(rows)
 assert r['drift']['status']=='deterioration signal'
 assert r['drift']['weekly_log_loss_change_95'][0]>0
 assert 'do not assume an injury caused a loss' in ' '.join(r['actions'])
