"""Report NFL/NBA first and NHL next from an existing public snapshot."""
import argparse,json
from pathlib import Path
from sportslab.priority_review import review
p=argparse.ArgumentParser();p.add_argument('--snapshot',default='web/data/snapshot.json');p.add_argument('--output',default='artifacts/research/priority-saved-predictions.json');args=p.parse_args()
snapshot=json.loads(Path(args.snapshot).read_text());reports={}
for name in ('NFL','NBA','NHL'):
 league=next(l for l in snapshot['leagues'] if l['name']==name);report=review(name,league.get('prediction_archive',league.get('prediction_history',[])),league.get('injury_research',{}));reports[name]=report
 print(name,json.dumps({'performance':report['saved_predictions'],'calibration':report['calibration_review'],'findings':report['findings']}),flush=True)
Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps({'source_generated_at':snapshot['generated_at'],'leagues':reports},allow_nan=False))
