from datetime import datetime,timezone
import json
from sportslab.pages import prediction_history,prediction_record
from sportslab.lifecycle import record

ASOF=datetime(2026,11,8,23,tzinfo=timezone.utc)
def pick(identity='one',policy='old',correct=False,generated='2026-09-01T10:00:00+00:00'):
 return {'id':identity,'date':'2026-09-01','event_start_utc':'2026-09-01T20:00:00+00:00','home':'A','away':'B','home_probability':.7,'generated_at':generated,'prediction_policy':policy,'model':'logistic','dataset_sha256':'abc','correct':correct,'outcome':'away' if correct is False else 'home','result_status':'graded'}

def test_all_time_counts_first_pick_once_across_policies_not_best_outcome():
 a=pick();b=pick(policy='new',correct=True,generated='2026-09-01T11:00:00+00:00');c=pick('two',correct=True)
 report=prediction_record([a,b,c],ASOF)
 assert report['recorded']==2 and report['correct']==1 and report['incorrect']==1 and report['accuracy']==.5
 report=prediction_record([dict(a,result_status='not_pregame',correct=None),b],ASOF)
 assert report['correct']==1

def test_all_time_retains_old_saved_games_and_persisted_labels(tmp_path):
 a=pick();a.update(settled=True,final_outcome='away')
 (tmp_path/'state.json').write_text(json.dumps({'ledger':{'one':a}}))
 assert prediction_history(tmp_path,[],ASOF)==[]
 history=prediction_history(tmp_path,[],ASOF,days=None,include_scheduled=True)
 assert len(history)==1 and history[0]['correct'] is False
 assert prediction_record(history,ASOF)['incorrect']==1

def test_future_and_unresolved_games_do_not_enter_accuracy_denominator():
 a=pick();b=dict(pick('future'),event_start_utc='2026-11-09T20:00:00+00:00',correct=None,outcome=None,result_status='pending');c=dict(pick('missing'),correct=None,outcome=None,result_status='awaiting_result');d=dict(pick('canceled'),correct=None,outcome=None,result_status='canceled')
 r=prediction_record([a,b,c,d],ASOF)
 assert r['recorded']==4 and r['graded']==1 and r['accuracy']==0
 assert r['scheduled']==1 and r['awaiting_result']==1 and r['unscored']==1

def test_record_preserves_original_probability_and_original_injury_context(tmp_path):
 (tmp_path/'state.json').write_text(json.dumps({'ledger':{},'consumed_losses':0}))
 a=pick();a['injury_context']={'status':'review_required','checked':'2026-09-01T09:00:00Z','teams':{'A':[{'player':'Player','status':'Out'}]}}
 record(tmp_path,[a]);b=dict(a,home_probability=.9,injury_context={'status':'report_checked'})
 record(tmp_path,[b]);saved=json.loads((tmp_path/'state.json').read_text())['ledger']['one']
 assert saved['home_probability']==.7 and saved['injury_context']==a['injury_context']
