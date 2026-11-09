import gzip,hashlib,json,os
from datetime import datetime,timezone,timedelta
from sportslab.storage import archive_bytes,maintain

NOW=datetime(2026,11,9,tzinfo=timezone.utc)
def raw_file(root,data):
 directory=root/'sources';directory.mkdir(exist_ok=True);path=directory/(hashlib.sha256(data).hexdigest()+'.raw');path.write_bytes(data);os.utime(path,(NOW.timestamp(),NOW.timestamp()));return path

def test_existing_raw_archives_compress_losslessly_and_protected_records_survive(tmp_path):
 data=b'original results '*1000;path=raw_file(tmp_path,data)
 for name in ('lab.sqlite3','public-lifecycle/NBA/state.json','public-injuries/research/NBA.json','models/champion.joblib','public-props/NBA.json'):
  p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'unchanged')
 result=maintain(tmp_path,NOW)
 assert result['compressed_files']==1 and result['source_after_bytes']<result['source_before_bytes']
 assert not path.exists() and gzip.decompress(path.with_suffix('.raw.gz').read_bytes())==data
 assert all((tmp_path/name).read_bytes()==b'unchanged' for name in ('lab.sqlite3','public-lifecycle/NBA/state.json','public-injuries/research/NBA.json','models/champion.joblib','public-props/NBA.json'))

def test_new_archives_deduplicate_and_enforce_replaceable_cache_budget(tmp_path):
 data=b'results';digest=archive_bytes(tmp_path,data);archive_bytes(tmp_path,data)
 assert len(list((tmp_path/'sources').iterdir()))==1
 assert gzip.decompress(next((tmp_path/'sources').iterdir()).read_bytes())==data
 maintain(tmp_path,datetime.now(timezone.utc),source_limit=0)
 assert not list((tmp_path/'sources').iterdir())

def test_unknown_or_checksum_mismatched_files_are_preserved(tmp_path):
 directory=tmp_path/'sources';directory.mkdir();(directory/'user.csv').write_text('mine');bad=directory/('0'*64+'.raw');bad.write_text('bad digest')
 result=maintain(tmp_path,NOW)
 assert (directory/'user.csv').read_text()=='mine' and bad.read_text()=='bad digest'
 assert result['invalid_source_files_preserved']==[bad.name]

def test_old_injury_archives_and_extra_backups_pruned_but_research_retained(tmp_path):
 directory=tmp_path/'public-injuries'/'archives'/'NBA';directory.mkdir(parents=True);p=directory/'old.json.gz';p.write_bytes(b'old');os.utime(p,(0,0))
 backups=tmp_path/'backups';backups.mkdir()
 for i in range(10):(backups/f'sportslab-{i}.tar.gz').write_bytes(b'backup')
 r=maintain(tmp_path,NOW)
 assert r['removed_injury_archives']==1 and len(list(backups.iterdir()))==7


def test_backup_and_restore_include_prediction_and_injury_research_without_auth(tmp_path):
 import subprocess,sys
 from sportslab.data import connect
 root=tmp_path/'runtime'
 with connect(root) as db:pass
 for name in ('public-lifecycle/NBA/state.json','public-injuries/research/NBA.json'):
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"saved":"unchanged"}')
 (root/'auth.json').write_text('secret never archived')
 archive_bytes(root,b'original source')
 env=dict(os.environ,SPORTSLAB_HOME=str(root));destination=tmp_path/'backups'
 process=subprocess.run([sys.executable,'-m','scripts.backup',str(destination)],env=env,text=True,capture_output=True,check=True)
 archive=process.stdout.strip();restored=tmp_path/'restored'
 subprocess.run([sys.executable,'-m','scripts.restore',archive,str(restored)],text=True,capture_output=True,check=True)
 for name in ('public-lifecycle/NBA/state.json','public-injuries/research/NBA.json'):assert (restored/name).read_text()=='{"saved":"unchanged"}'
 assert not (restored/'auth.json').exists()
 assert gzip.decompress(next((restored/'sources').glob('*.gz')).read_bytes())==b'original source'


def test_concurrent_identical_source_downloads_remain_one_valid_archive(tmp_path):
 from concurrent.futures import ThreadPoolExecutor
 data=b'one shared response'*1000
 with ThreadPoolExecutor(max_workers=8) as pool:hashes=list(pool.map(lambda _:archive_bytes(tmp_path,data),range(20)))
 assert len(set(hashes))==1
 files=list((tmp_path/'sources').iterdir());assert len(files)==1 and gzip.decompress(files[0].read_bytes())==data
