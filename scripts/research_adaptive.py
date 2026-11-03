"""Run bounded adaptive studies on verified public data without changing live models."""
import argparse
import json
from pathlib import Path
import joblib
from sportslab.data import connect
from sportslab.pages import public_rows
from sportslab.adaptive import saved_review

p=argparse.ArgumentParser();p.add_argument('--runtime',default='/workspace/.sportsml-private');p.add_argument('--output',default='artifacts/research/adaptive-error-v1.json');p.add_argument('--snapshot',default='web/data/snapshot.json');args=p.parse_args()
root=Path(args.runtime);reports={};public=json.loads(Path(args.snapshot).read_text())
with connect(root) as db:
 for league in ('NBA','NFL','NHL','MLB','CFB','WNBA','UFC'):
  rows=[r for r in public_rows(db,league) if r['outcome'] in ('home','away')];directory=root/'public-lifecycle'/league
  files=[f for f in sorted(Path('artifacts').glob(league+'-*.json')) if not f.name.endswith('-heldout.json')]
  if files:report=json.loads(files[0].read_text())
  elif (directory/'initial-report.json').exists():report=json.loads((directory/'initial-report.json').read_text())
  else:
   live=next((l for l in public['leagues'] if l['name']==league),None)
   report=live.get('benchmark') if live else None
   if not report:print(league,'no verified baseline',flush=True);continue
  if len(rows)<700:print(league,'insufficient verified public history',flush=True);continue
  if (directory/'champion.joblib').exists():
   champion=joblib.load(directory/'champion.joblib');previous=json.loads((directory/'research-review.json').read_text()) if (directory/'research-review.json').exists() else None
  else:
   from sportslab.research import incumbent_spec
   live=next(l for l in public['leagues'] if l['name']==league)
   if (live.get('lifecycle') or {}).get('champion')!=report['selected']:print(league,'current champion metadata requires runtime cache',flush=True);continue
   champion={'selected':report['selected'],'research_spec':incumbent_spec(report)};previous=live['lifecycle']['backtest_review'];directory=root/'offline-adaptive'/league
  result=saved_review(directory,rows,report,champion,previous)
  if league=='NBA' and (directory/'nba-recent-review.json').exists():
   from sportslab.adaptive import saved_recent_review
   result['recent_data_research']=saved_recent_review(directory,rows,json.loads((directory/'nba-recent-review.json').read_text()))
  reports[league]=result
  print(league,json.dumps({'selected':result['selected'],'new_method_selected':result['new_method_selected'],'incumbent':result['incumbent']['validation'],'best':result['best']['validation']}),flush=True)
Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps({'version':'adaptive-error-review-v1','leagues':reports},allow_nan=False))
