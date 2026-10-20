import argparse
import json
import os
from sportslab.data import connect
from sportslab.model import train
p=argparse.ArgumentParser(); p.add_argument('--league',default='NBA'); args=p.parse_args()
root=os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'); db=connect(root)
print(json.dumps(train(db,root,args.league),indent=2)); db.close()
