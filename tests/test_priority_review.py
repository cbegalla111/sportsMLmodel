import copy,math
from datetime import date,timedelta
from sportslab.priority_review import review

def rows():
 return [{'id':str(i),'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'generated_at':(date(2026,1,1)+timedelta(days=i)).isoformat()+'T10:00:00Z','home':'A','away':'B','home_probability':.8,'result_status':'graded','outcome':'home' if i%3 else 'away','correct':bool(i%3)} for i in range(90)]

def test_priority_order_and_no_live_promotion_or_unvalidated_injury_effect():
 for league,priority in [('NFL',1),('NBA',2),('NHL',3)]:
  r=review(league,rows(),{'settled':12,'minimum_settled':200});assert r['priority']==priority and r['saved_predictions']['n']==90
  assert not r['production_changed'] and not r['injury_adjustment_approved'] and not r['calibration_review']['promotion_allowed']
 assert review('MLB',rows(),{}) is None

def test_later_outcomes_cannot_select_calibration_specification():
 original=rows();a=review('NBA',original,{})
 changed=copy.deepcopy(original)
 for r in changed[60:]:r.update(outcome='away',correct=False)
 b=review('NBA',changed,{})
 assert a['calibration_review']['selected']==b['calibration_review']['selected']
 assert a['calibration_review']['baseline_check']!=b['calibration_review']['baseline_check']

def test_duplicate_versions_and_unscored_rows_do_not_inflate_sample():
 original=rows();duplicates=[dict(r,generated_at=r['generated_at'].replace('10:','12:'),home_probability=.99) for r in original]
 report=review('NFL',original+duplicates+[dict(original[0],id='late',result_status='not_pregame')],{})
 assert report['saved_predictions']['n']==90
 assert report['saved_predictions']['log_loss']==review('NFL',original,{})['saved_predictions']['log_loss']
