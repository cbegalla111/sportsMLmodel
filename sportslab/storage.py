"""Bound replaceable source caches without touching fitted models or prediction ledgers."""
from datetime import datetime,timedelta,timezone
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile

SOURCE_LIMIT=128*1024*1024
INJURY_ARCHIVE_LIMIT=64*1024*1024
HASH_FILE=re.compile(r'^[0-9a-f]{64}\.(?:raw|csv)(?:\.gz)?$')

def archive_bytes(root,raw,suffix='raw'):
 if suffix not in ('raw','csv'):raise ValueError('Unsupported archive format')
 digest=hashlib.sha256(raw).hexdigest();directory=Path(root)/'sources';directory.mkdir(parents=True,exist_ok=True);path=directory/(digest+'.'+suffix+'.gz')
 if not path.exists():
  descriptor,name=tempfile.mkstemp(prefix=digest+'-',suffix='.tmp',dir=directory);os.close(descriptor);temp=Path(name)
  try:
   with gzip.open(temp,'wb',compresslevel=6) as f:f.write(raw)
   temp.replace(path)
  finally:temp.unlink(missing_ok=True)
 return digest

def size(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink()) if Path(root).exists() else 0

def prune(files,limit,cutoff):
 removed=0;freed=0;files=sorted([p for p in files if p.is_file() and not p.is_symlink()],key=lambda p:p.stat().st_mtime,reverse=True);used=0
 for p in files:
  info=p.stat()
  if info.st_mtime<cutoff or used+info.st_size>limit:
   p.unlink();removed+=1;freed+=info.st_size
  else:used+=info.st_size
 return removed,freed

def maintain(root,asof=None,source_limit=SOURCE_LIMIT,injury_limit=INJURY_ARCHIVE_LIMIT):
 root=Path(root);asof=asof or datetime.now(timezone.utc);directory=root/'sources';before=size(directory);compressed=0;invalid=[]
 for path in directory.iterdir() if directory.exists() else []:
  if path.is_symlink() or not path.is_file() or not HASH_FILE.fullmatch(path.name) or path.suffix not in ('.raw','.csv'):continue
  stamp=path.stat().st_mtime
  digest=hashlib.sha256()
  with path.open('rb') as src:
   for chunk in iter(lambda:src.read(1024*1024),b''):digest.update(chunk)
  if digest.hexdigest()!=path.name.split('.')[0]:invalid.append(path.name);continue
  target=path.with_suffix(path.suffix+'.gz');temp=target.with_suffix(target.suffix+'.tmp')
  with path.open('rb') as src,gzip.open(temp,'wb',compresslevel=6) as dst:shutil.copyfileobj(src,dst)
  check=hashlib.sha256()
  with gzip.open(temp,'rb') as src:
   for chunk in iter(lambda:src.read(1024*1024),b''):check.update(chunk)
  if check.hexdigest()!=digest.hexdigest():temp.unlink();raise ValueError('Compressed source verification failed')
  temp.replace(target);os.utime(target,(stamp,stamp));path.unlink();compressed+=1
 archives=[p for p in directory.glob('*.gz') if HASH_FILE.fullmatch(p.name)] if directory.exists() else []
 removed,freed=prune(archives,source_limit,(asof-timedelta(days=30)).timestamp())
 injury_dir=root/'public-injuries'/'archives';injury_removed,injury_freed=prune(list(injury_dir.glob('*/*.json.gz')),injury_limit,(asof-timedelta(days=180)).timestamp())
 backups=sorted((root/'backups').glob('sportslab-*.tar.gz'),key=lambda p:p.stat().st_mtime,reverse=True)
 for p in backups[7:]:
  if p.is_file() and not p.is_symlink():p.unlink()
 return {'source_before_bytes':before,'source_after_bytes':size(directory),'compressed_files':compressed,'removed_source_files':removed,'removed_injury_archives':injury_removed,'invalid_source_files_preserved':invalid,'source_limit_bytes':source_limit,'injury_archive_limit_bytes':injury_limit,'backup_count_kept':min(7,len(backups)),'protected':'Database, model weights, prediction ledgers, injury research features and player logs are never pruned.'}
