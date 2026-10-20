import http.cookiejar
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
import urllib.request
import urllib.error
import pytest
from sportslab import server

@pytest.fixture
def app(tmp_path,monkeypatch):
 monkeypatch.setattr(server,'ROOT',tmp_path);server.SESSIONS.clear();server.ATTEMPTS.clear();server.initialize(tmp_path)
 httpd=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
 base='http://127.0.0.1:'+str(httpd.server_port);jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 def call(path,body=None,headers={}):
  req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**headers})
  try:
   with client.open(req) as r:return r.status,json.load(r),r.headers
  except urllib.error.HTTPError as e:return e.code,json.load(e),e.headers
 yield call,tmp_path
 httpd.shutdown();httpd.server_close()

def test_authentication_csrf_logout_and_persisted_settings(app):
 call,root=app
 assert call('/api/state')[0]==401
 assert call('/api/login',{'password':'wrong'})[0]==401
 code,_,headers=call('/api/login',{'password':(root/'initial-password.txt').read_text().strip()});assert code==200
 assert 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=Strict' in headers['Set-Cookie']
 state=call('/api/state')[1];h={'X-CSRF-Token':state['csrf']}
 assert call('/api/settings',{'league':'NFL'})[0]==403
 assert call('/api/settings',{'league':'NFL'},{**h,'Origin':'https://evil.example'})[0]==403
 assert call('/api/settings',{'league':'NFL'},h)[0]==200
 assert call('/api/state')[1]['settings']['league']=='NFL'
 assert 'default-src' in headers['Content-Security-Policy']
 assert call('/api/logout',{},h)[0]==200
 assert call('/api/state')[0]==401

def test_login_rate_limit(app):
 call,_=app
 for _ in range(10):assert call('/api/login',{'password':'bad'})[0]==401
 assert call('/api/login',{'password':'bad'})[0]==429
