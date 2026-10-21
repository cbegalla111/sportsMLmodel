import argparse
import json
import os
from pathlib import Path
import time
import subprocess
import sys
from sportslab.data import connect, ingest, parse_csv, now
from sportslab.refresh import run
from sportslab.model import refit_frozen
p=argparse.ArgumentParser(); p.add_argument('--watch',action='store_true'); p.add_argument('--interval',type=int,default=86400); args=p.parse_args()
if args.interval<3600: p.error('Minimum automatic interval is one hour; default one day')
root=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'))
root.mkdir(parents=True,exist_ok=True); root.chmod(0o700)
for folder in ('inbox','processed','rejected'): (root/folder).mkdir(exist_ok=True)
while True:
 results=run(root)
 db=connect(root)
 for file in sorted((root/'inbox').glob('*.csv')):
  try:
   if file.stat().st_size>15_000_000: raise ValueError('Inbox file too large')
   ingest(db,parse_csv(file.read_text())); file.rename(root/'processed'/(str(time.time_ns())+'-'+file.name))
  except Exception as e:
   dest=root/'rejected'/(str(time.time_ns())+'-'+file.name); file.rename(dest); dest.with_suffix('.error.txt').write_text(str(e))
 refits={}
 for league in ('NBA','NFL','MLB','NHL','CFB','WNBA','UFC'):
  try: refits[league]=refit_frozen(db,root,league)
  except Exception as e: refits[league]='error: '+str(e)
 with db: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('last_automatic_refresh',json.dumps({'finished':now(),'refits':refits})))
 backup_day=time.strftime('%Y-%m-%d',time.gmtime())
 last_backup=db.execute('SELECT value FROM settings WHERE key=?',('last_backup',)).fetchone()
 if not last_backup or last_backup[0]!=backup_day:
  done=subprocess.run([sys.executable,'-m','scripts.backup',str(root/'backups')],capture_output=True,text=True)
  if done.returncode==0:
   with db: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('last_backup',backup_day))
   backups=sorted((root/'backups').glob('sportslab-*.tar.gz'))
   for old in backups[:-7]:old.unlink()
  else: refits['backup']='failed: '+done.stderr[-500:]
 db.close()
 print(json.dumps({'feeds':[{k:r.get(k) for k in ('league','status','checked','accepted_rows','latest_result','error')} for r in results],'refits':refits}),flush=True)
 if not args.watch: break
 time.sleep(args.interval)
