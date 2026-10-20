"""Export actual model artifacts and reproduce only the already-selected held-out predictions.
No model selection is repeated and no specification is changed.
"""
import json
import os
from pathlib import Path
import shutil
import numpy as np
from sportslab.data import connect, load
from sportslab.model import features, estimator, elo, evaluate
root=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private')); db=connect(root); dest=Path('artifacts');dest.mkdir(exist_ok=True)
for record in db.execute('SELECT payload FROM experiments').fetchall():
 r=json.loads(record[0]);rows=[g for g in load(db,r['league']) if g['outcome'] in ('home','away')]
 kind='boost' if r['selected'].startswith('boost') else 'logistic'
 import joblib
 art=joblib.load(root/'models'/(r['id']+'.joblib'));built,_=features(rows,art['window'],art['extra']);X=np.array([v[1] for v in built]);y=np.array([int(v[0]['outcome']=='home') for v in built]);ds=np.array([v[0]['date'] for v in built]);warm=np.array([v[2]>=5 for v in built]);tr=(ds<r['final_test_start'])&warm;te=(ds>=r['final_test_start'])&warm
 if r['selected'].startswith('elo'):p=elo(X[te])
 else:
  m=estimator(kind);m.fit(X[tr],y[tr]);p=m.predict_proba(X[te])[:,1]
 metrics=evaluate(y[te],p,list(ds[te]),r['league'])
 assert abs(metrics['brier']-r['test']['brier'])<1e-12
 assert abs(metrics['log_loss']-r['test']['log_loss'])<1e-12
 r['test']=metrics
 art['neutral_variation']=len(np.unique(X[warm,1]))>1;joblib.dump(art,root/'models'/(r['id']+'.joblib'))
 with db: db.execute('UPDATE experiments SET payload=? WHERE id=?',(json.dumps(r),r['id']))
 (dest/(r['id']+'.json')).write_text(json.dumps(r,indent=2)+'\n');shutil.copy2(root/'models'/(r['id']+'.joblib'),dest)
 (dest/(r['id']+'-heldout.json')).write_text(json.dumps([{'date':d,'observed_home_win':int(yy),'home_probability':float(pp)} for d,yy,pp in zip(ds[te],y[te],p)],indent=2)+'\n')
 print(r['id'],'exported; exact test scores reproduced')
db.close()
