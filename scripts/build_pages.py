"""Build a public-only static dashboard; raw inputs stay in a separate private runtime."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from sportslab.data import connect
from sportslab.pages import export_snapshot,write_site
from sportslab.refresh import run
from sportslab.lifecycle import checkpoint_public_lineage
p=argparse.ArgumentParser();p.add_argument('--runtime',default=os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'));p.add_argument('--output',default='_site');p.add_argument('--refresh',action='store_true');args=p.parse_args()
root=Path(args.runtime).resolve();env=dict(os.environ,SPORTSLAB_HOME=str(root),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
if args.refresh:
 checkpoint_public_lineage(root,Path('artifacts'))
 with connect(root) as db:
  nba_empty=db.execute("SELECT COUNT(*) FROM games WHERE league='NBA'").fetchone()[0]==0
 if nba_empty:
  result=subprocess.run([sys.executable,'-m','scripts.import_nba'],env=env)
  if result.returncode:print('Archived NBA source unavailable; no data substituted.',flush=True)
 print('Public feed statuses:',[{k:f.get(k) for k in ('league','status','latest_result','error')} for f in run(root)],flush=True)
 with connect(root) as db:nhl_small=db.execute("SELECT COUNT(*) FROM games WHERE league='NHL'").fetchone()[0]<700
 if nhl_small:
  result=subprocess.run([sys.executable,'-m','scripts.backfill_nhl'],env=env)
  if result.returncode:print('NHL backfill incomplete; forecasts will be withheld if history fails validation.',flush=True)
if args.refresh:
 from sportslab.nba_box import refresh_history
 from sportslab.pages import public_rows
 with connect(root) as db:nba_rows=public_rows(db,'NBA')
 print('NBA box-score research source:',refresh_history(root,nba_rows),flush=True)
snapshot=export_snapshot(root,Path('artifacts'))
write_site(snapshot,Path(args.output),Path.cwd())
print('Built public dashboard:',[(s['name'],s['result_count'],len(s['predictions'])) for s in snapshot['leagues']],flush=True)

summary=os.environ.get('GITHUB_STEP_SUMMARY')
if summary:
 with open(summary,'a') as f:
  f.write('## Daily public data and model outputs\n\n| Sport | Results | Active forecasts at export | Feed |\n|---|---:|---:|---|\n')
  for item in snapshot['leagues']:
   f.write(f"| {item['name']} | {item['result_count']} | {len(item['predictions'])} | {item['feed_status']} |\n")
  f.write('\nHistorical test scores remain sealed. Losses trigger prospective challenger review; weights change only if every improvement check passes. Missing/stale inputs withhold forecasts.\n')
