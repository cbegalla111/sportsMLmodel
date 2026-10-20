"""Restore a verified backup to a NEW empty private directory. Never overwrite user data."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import tarfile
p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('destination');args=p.parse_args()
dest=Path(args.destination)
if dest.exists() and any(dest.iterdir()):p.error('Destination must be new or empty')
dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
with tarfile.open(args.archive,'r:gz') as tar:
 for m in tar.getmembers():
  if Path(m.name).is_absolute() or '..' in Path(m.name).parts or m.issym() or m.islnk():raise ValueError('Unsafe archive member')
 tar.extractall(dest,filter='data')
manifest=json.loads((dest/'manifest.json').read_text())
for rel,sha in manifest.items():
 file=dest/rel
 if not file.resolve().is_relative_to(dest.resolve()):raise ValueError('Unsafe manifest path')
 if hashlib.sha256(file.read_bytes()).hexdigest()!=sha:raise ValueError('Backup checksum mismatch: '+rel)
with sqlite3.connect(dest/'lab.sqlite3') as db:
 if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed')
 print('Restored and verified',db.execute('SELECT COUNT(*) FROM games').fetchone()[0],'events and',db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0],'predictions')
print('Authentication is intentionally excluded; initialize the server to generate a new password.')
