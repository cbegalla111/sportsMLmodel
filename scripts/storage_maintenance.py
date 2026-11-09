"""Compress and bound replaceable caches in the selected runtime."""
import argparse,json,os
from sportslab.storage import maintain
p=argparse.ArgumentParser();p.add_argument('--runtime',default=os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'));args=p.parse_args()
print(json.dumps(maintain(args.runtime)),flush=True)
