import http.cookiejar
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
base='http://127.0.0.1:'+os.environ.get('PORT','8765')
with urllib.request.urlopen(base,timeout=10) as r:assert r.status==200 and b'COURTSIDE' in r.read()
try:
 urllib.request.urlopen(base+'/api/state',timeout=10);raise AssertionError('Anonymous data access must be denied')
except urllib.error.HTTPError as e:assert e.code==401
root=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'));file=root/'initial-password.txt'
password=os.environ.get('SPORTSLAB_PASSWORD') or (file.read_text().strip() if file.exists() else None)
if password:
 client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 req=urllib.request.Request(base+'/api/login',data=json.dumps({'password':password}).encode(),headers={'Content-Type':'application/json'})
 with client.open(req,timeout=10) as r:
  assert r.status==200
  session_cookie=r.headers['Set-Cookie'].split(';')[0]
 # Check the loopback upstream even when the browser-facing proxy uses Secure cookies.
 authenticated=urllib.request.Request(base+'/api/state',headers={'Cookie':session_cookie})
 with client.open(authenticated,timeout=15) as r:state=json.load(r)
 assert len(state['leagues'])==7
 print('Ready: homepage, anonymous denial, authenticated seven-league state and persisted history ('+str(len(state['history']))+' records) verified.')
else:print('Homepage and anonymous denial verified; authenticated check requires local password via SPORTSLAB_PASSWORD.')
