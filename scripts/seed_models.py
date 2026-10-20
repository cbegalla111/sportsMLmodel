"""Restore committed benchmark artifacts only after verifying their historical data digest."""
import json
import os
from pathlib import Path
import shutil
from sportslab.data import connect, load, version
from sportslab.model import refit_frozen
root=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'));db=connect(root);(root/'models').mkdir(exist_ok=True)
for file in Path('artifacts').glob('*.json'):
 if file.name.endswith('-heldout.json'):continue
 r=json.loads(file.read_text())
 if db.execute('SELECT 1 FROM experiments WHERE league=?',(r['league'],)).fetchone():continue
 history=[g for g in load(db,r['league']) if g['outcome'] in ('home','away') and g['date']<=r['last_date']]
 if version(history)!=r['dataset_sha256']:
  print(r['league']+': archived benchmark not restored: source digest differs; initial validation required');continue
 target=root/'models'/(r['id']+'.joblib')
 if not target.exists():shutil.copy2(file.with_suffix('.joblib'),target)
 with db:db.execute('INSERT INTO experiments VALUES(?,?,?,?)',(r['id'],r['league'],r['created'],json.dumps(r)))
 print(r['league']+': verified archived benchmark restored; '+refit_frozen(db,root,r['league']))
db.close()
