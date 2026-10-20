import argparse
import base64
import hashlib
import hmac
import http.cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlparse
from .data import LEAGUES, FEATURES, connect, ingest, load, now, parse_csv
from .model import train, predict

ROOT=Path(os.environ.get('SPORTSLAB_HOME','/workspace/.sportsml-private'))
WEB=Path(__file__).resolve().parent.parent
SESSIONS={}; ATTEMPTS={}; LOCK=threading.Lock()

def initialize(root):
 root.mkdir(parents=True,exist_ok=True); root.chmod(0o700)
 auth=root/'auth.json'
 if not auth.exists():
  password=secrets.token_urlsafe(24); salt=secrets.token_hex(16)
  record={'salt':salt,'hash':hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()}
  fd=os.open(auth,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f: json.dump(record,f)
  fd=os.open(root/'initial-password.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f: f.write(password+'\n')
 connect(root).close()

class Handler(BaseHTTPRequestHandler):
 def log_message(self,fmt,*args): pass  # No request payloads, cookies or credentials in logs.
 def respond(self,status,payload,ctype='application/json',cookie=None):
  data=json.dumps(payload).encode() if ctype=='application/json' else payload.encode()
  self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data)))
  self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('X-Frame-Options','DENY'); self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
  if cookie: self.send_header('Set-Cookie',cookie)
  self.end_headers(); self.wfile.write(data)
 def session(self):
  try:
   cookie=http.cookies.SimpleCookie(self.headers.get('Cookie','')); sid=cookie['session'].value
   s=SESSIONS.get(sid)
   return s if s and s['expires']>time.time() else None
  except (KeyError,http.cookies.CookieError): return None
 def body(self):
  n=int(self.headers.get('Content-Length','0'))
  if not 0<n<=15_000_000: raise ValueError('Body must be 1 byte to 15 MB')
  return json.loads(self.rfile.read(n))
 def do_GET(self):
  path=urlparse(self.path).path
  if path in ('/','/app.js','/style.css'):
   file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
   return self.respond(200,(WEB/'static'/file).read_text(),{'/':'text/html; charset=utf-8','/app.js':'text/javascript','/style.css':'text/css'}[path])
  s=self.session()
  if not s: return self.respond(401,{'error':'Authentication required'})
  db=connect(ROOT)
  try:
   if path=='/api/state':
    leagues=[]
    for league in LEAGUES:
     rows=load(db,league); ex=db.execute('SELECT payload FROM experiments WHERE league=? ORDER BY created DESC LIMIT 1',(league,)).fetchone()
     leagues.append({'name':league,'n':len(rows),'data_through':rows[-1]['date'] if rows else None,'teams':sorted({r[k] for r in rows for k in ('home','away')}),'features':FEATURES[league],'sources':sorted({r['source'] for r in rows}),'experiment':json.loads(ex[0]) if ex else None})
    history=[]
    for r in db.execute('SELECT id,created,payload FROM predictions ORDER BY id DESC LIMIT 100'):
     p=json.loads(r['payload']); match=[g for g in load(db,p['league']) if g['date']==p['date'] and g['home']==p['home'] and g['away']==p['away']]
     history.append(dict(p,id=r['id'],created=r['created'],eventual_outcome=match[0]['outcome'] if match else 'not recorded'))
    settings={r[0]:r[1] for r in db.execute('SELECT key,value FROM settings')}
    return self.respond(200,{'leagues':leagues,'history':history,'csrf':s['csrf'],'settings':settings,'server_time':now()})
   return self.respond(404,{'error':'Not found'})
  finally: db.close()
 def do_POST(self):
  # Require same-origin JSON requests even for login; no CORS is enabled.
  origin=self.headers.get('Origin')
  expected=('https' if os.environ.get('SPORTSLAB_SECURE_COOKIE')=='1' else 'http')+'://'+self.headers.get('Host','')
  if origin and origin!=expected: return self.respond(403,{'error':'Origin rejected'})
  if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.respond(415,{'error':'JSON required'})
  try:
   body=self.body(); path=urlparse(self.path).path
   if path=='/api/login':
    ip=self.client_address[0]; attempts=[t for t in ATTEMPTS.get(ip,[]) if time.time()-t<300]
    ATTEMPTS[ip]=attempts
    if len(attempts)>=10: return self.respond(429,{'error':'Too many attempts; wait five minutes'})
    record=json.loads((ROOT/'auth.json').read_text()); password=str(body.get('password',''))
    candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(record['salt']),600000).hex()
    if not hmac.compare_digest(candidate,record['hash']):
     attempts.append(time.time()); return self.respond(401,{'error':'Incorrect password'})
    sid=secrets.token_urlsafe(32); SESSIONS[sid]={'expires':time.time()+8*3600,'csrf':secrets.token_urlsafe(32)}
    suffix='; Secure' if os.environ.get('SPORTSLAB_SECURE_COOKIE')=='1' else ''
    return self.respond(200,{'ok':True},cookie=f'session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+suffix)
   s=self.session()
   if not s: return self.respond(401,{'error':'Authentication required'})
   if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.respond(403,{'error':'CSRF token required'})
   db=connect(ROOT)
   try:
    if path=='/api/logout':
     cookie=http.cookies.SimpleCookie(self.headers.get('Cookie','')); SESSIONS.pop(cookie['session'].value,None)
     return self.respond(200,{'ok':True},cookie='session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
    if path=='/api/import': return self.respond(200,{'accepted_rows':ingest(db,parse_csv(body['csv']))})
    if path=='/api/manual': return self.respond(200,{'accepted_rows':ingest(db,[body['game']])})
    if path=='/api/train':
     if not LOCK.acquire(blocking=False): return self.respond(409,{'error':'Another experiment is running'})
     try: result=train(db,ROOT,body['league'])
     finally: LOCK.release()
     return self.respond(200,result)
    if path=='/api/predict': return self.respond(200,predict(db,ROOT,**body))
    if path=='/api/settings':
     if body.get('league') not in LEAGUES: raise ValueError('Invalid league')
     with db: db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('league',body['league']))
     return self.respond(200,{'ok':True})
    return self.respond(404,{'error':'Not found'})
   finally: db.close()
  except (ValueError,KeyError,TypeError) as e: self.respond(400,{'error':str(e)})
  except Exception:
   import traceback
   traceback.print_exc()
   self.respond(500,{'error':'Internal operation failed; inspect private server log'})

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8765); args=parser.parse_args()
 initialize(ROOT)
 print(f'Private local service on {args.host}:{args.port}; password file: {ROOT}/initial-password.txt',flush=True)
 ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
if __name__=='__main__': main()
