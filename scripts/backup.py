"""Consistent SQLite backup + model/source files; excludes authentication secrets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile
p=argparse.ArgumentParser(); p.add_argument('destination'); args=p.parse_args()
root=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private')); dest=Path(args.destination); dest.mkdir(parents=True,exist_ok=True); dest.chmod(0o700)
name='sportslab-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.tar.gz'
with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp)
 with sqlite3.connect(root/'lab.sqlite3') as src, sqlite3.connect(tmp/'lab.sqlite3') as dst: src.backup(dst)
 for folder in ('models','sources'):
  if (root/folder).exists(): shutil.copytree(root/folder,tmp/folder)
 files={str(f.relative_to(tmp)):hashlib.sha256(f.read_bytes()).hexdigest() for f in tmp.rglob('*') if f.is_file()}
 (tmp/'manifest.json').write_text(json.dumps(files,indent=2))
 with tarfile.open(dest/name,'w:gz') as tar:
  for f in tmp.iterdir(): tar.add(f,arcname=f.name)
(dest/name).chmod(0o600); print(dest/name)
