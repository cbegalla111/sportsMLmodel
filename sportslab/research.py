"""Bounded chronological model research. Archived final-test dates are never tuned."""
from collections import defaultdict,deque
from datetime import date,timedelta
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Ridge, PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.kernel_approximation import Nystroem
from sklearn.neural_network import MLPClassifier
from .data import now,version
from .model import features,elo,scores

VERSION='sport-review-v9-targeted-calibration-horizons'
HALF_LIFE={'NBA':365,'WNBA':365,'NFL':730,'CFB':730,'MLB':180,'NHL':365,'UFC':730}

def form_features(rows,window=20):
 base,names=features(rows,window)
 names=names+['short_form_difference','opponent_strength_difference','opponent_adjusted_form_difference','form_volatility_difference','recent_workload_difference','layoff_log_difference','experience_log_difference']
 histories=defaultdict(lambda:deque(maxlen=window));activity=defaultdict(deque);last={};count=defaultdict(int);ratings=defaultdict(lambda:1500.);groups=defaultdict(list);extra={}
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  d=date.fromisoformat(day)
  def summary(team):
   h=list(histories[team]);wins=[v[0] for v in h]
   while activity[team] and (d-activity[team][0]).days>14:activity[team].popleft()
   return np.array([np.mean(wins[-3:]) if wins else .5,np.mean([v[1] for v in h]) if h else 1500.,np.mean([v[2] for v in h]) if h else 0.,np.std(wins) if wins else 0.,len(activity[team]),np.log1p(min(730,(d-last[team]).days)) if team in last else np.log1p(180),np.log1p(count[team])])
  for r in group:extra[r['event_id']]=(summary(r['home'])-summary(r['away'])).tolist()
  for r in group:
   if r['outcome'] not in ('home','away'):continue
   h,a=r['home'],r['away'];y=int(r['outcome']=='home');rh,ra=ratings[h],ratings[a]
   p=1/(1+10**(-(rh-ra+60*(1-int(r['neutral'])))/400));delta=20*(y-p)
   histories[h].append((y,ra,y-p,d));histories[a].append((1-y,rh,p-y,d));ratings[h]+=delta;ratings[a]-=delta;last[h]=last[a]=d;count[h]+=1;count[a]+=1;activity[h].append(d);activity[a].append(d)
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names

def profile_features(rows,window=20):
 if rows[0]['league']=='UFC':raise ValueError('Fight result encodings are not physical scoring statistics')
 base,names=form_features(rows,window);names=names+['trailing_points_for_difference','trailing_points_allowed_difference','normalized_margin_difference','margin_volatility_difference','venue_form_difference']
 history=defaultdict(lambda:deque(maxlen=window));groups=defaultdict(list);extra={}
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  def summary(team,venue):
   h=list(history[team]);v=[r[5] for r in h if r[4]==venue]
   return np.array([np.mean([r[0] for r in h]) if h else 0.,np.mean([r[1] for r in h]) if h else 0.,np.mean([r[2] for r in h]) if h else 0.,np.std([r[3] for r in h]) if h else 0.,(sum(v)+2.5)/(len(v)+5)])
  for r in group:
   x=summary(r['home'],'home')-summary(r['away'],'away')
   if r['neutral']=='1':x[-1]=0
   extra[r['event_id']]=x.tolist()
  for r in group:
   if r['outcome'] not in ('home','away'):continue
   h,a=r['home'],r['away'];hs,aws=float(r['home_score']),float(r['away_score']);margin=hs-aws;share=margin/max(1,hs+aws);win=int(r['outcome']=='home')
   history[h].append((hs,aws,share,margin,'home' if r['neutral']=='0' else None,win));history[a].append((aws,hs,-share,-margin,'away' if r['neutral']=='0' else None,1-win))
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names

def rating_features(rows,window=20):
 """Several causal strength scales; season regression happens before the event."""
 from .model import season
 base,names=features(rows,window);combat=rows[0]['league']=='UFC'
 names=names+['slow_rating_difference','fast_rating_difference','season_adjusted_rating_difference','ewma_win_difference']+([] if combat else ['margin_rating_difference','ewma_normalized_margin_difference'])
 ratings={k:defaultdict(float) for k in ('slow','fast','season','margin')};last_season={};last_day={};wins=defaultdict(lambda:.5);margins=defaultdict(float);groups=defaultdict(list);extra={}
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  d=date.fromisoformat(day);year=int(season(rows[0]['league'],day))
  def seasonal(t):
   elapsed=max(0,(d-last_day[t]).days)/365 if combat and t in last_day else max(0,year-last_season.get(t,year))
   return ratings['season'][t]*(.9 if combat else .75)**elapsed
  for r in group:
   h,a=r['home'],r['away'];x=[ratings['slow'][h]-ratings['slow'][a],ratings['fast'][h]-ratings['fast'][a],seasonal(h)-seasonal(a),wins[h]-wins[a]]
   if not combat:x.extend([ratings['margin'][h]-ratings['margin'][a],margins[h]-margins[a]])
   extra[r['event_id']]=x
  for r in group:
   if r['outcome'] not in ('home','away'):continue
   h,a=r['home'],r['away'];y=int(r['outcome']=='home');advantage=0 if combat or r['neutral']=='1' else {'NBA':65,'WNBA':55,'NFL':45,'CFB':55,'MLB':25,'NHL':35}[r['league']]
   for kind,k in (('slow',10),('fast',40),('season',24),*(() if combat else (('margin',20),))):
    rh,ra=(seasonal(h),seasonal(a)) if kind=='season' else (ratings[kind][h],ratings[kind][a])
    expected=1/(1+10**(-np.clip(rh-ra+advantage,-2000,2000)/400));multiplier=1.
    if kind=='margin':multiplier=min(2.,np.log1p(abs(float(r['home_score'])-float(r['away_score'])))/np.log(4))
    delta=k*multiplier*(y-expected);ratings[kind][h]=rh+delta;ratings[kind][a]=ra-delta
   wins[h]=.85*wins[h]+.15*y;wins[a]=.85*wins[a]+.15*(1-y)
   if not combat:
    hs,aws=float(r['home_score']),float(r['away_score']);share=(hs-aws)/max(1,hs+aws);margins[h]=.85*margins[h]+.15*share;margins[a]=.85*margins[a]-.15*share
   for t in (h,a):last_season[t]=year;last_day[t]=d
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names

def bayesian_features(rows,window=20):
 """Glicko-style dynamic uncertainty, calculated before each date's outcomes."""
 base,names=rating_features(rows,window);names=names+['uncertain_rating_difference','rating_deviation_difference','uncertainty_adjusted_log_odds','conservative_strength_difference']
 strength=defaultdict(lambda:1500.);deviation=defaultdict(lambda:350.);last={};groups=defaultdict(list);extra={};q=np.log(10)/400
 for r in rows:groups[r['date']].append(r)
 for day,group in sorted(groups.items()):
  d=date.fromisoformat(day);league=rows[0]['league'];drift={'NBA':20,'WNBA':20,'NFL':15,'CFB':20,'NHL':20,'MLB':12,'UFC':12}[league]
  teams={r[side] for r in group for side in ('home','away')}
  rd={t:min(350.,np.sqrt(deviation[t]**2+drift**2*max(0,(d-last[t]).days)/30)) if t in last else 350. for t in teams}
  g=lambda uncertainty:1/np.sqrt(1+3*q*q*uncertainty*uncertainty/(np.pi*np.pi))
  precision=defaultdict(float);gradient=defaultdict(float)
  for r in group:
   h,a=r['home'],r['away'];adv=0 if league=='UFC' or r['neutral']=='1' else {'NBA':65,'WNBA':55,'NFL':45,'CFB':55,'NHL':35,'MLB':25}[league]
   diff=strength[h]-strength[a]+adv;z=q*diff/np.sqrt(1+3*q*q*(rd[h]**2+rd[a]**2)/(np.pi*np.pi))
   extra[r['event_id']]=[strength[h]-strength[a],rd[h]-rd[a],float(z),(strength[h]-1.64*rd[h])-(strength[a]-1.64*rd[a])]
   if r['outcome'] not in ('home','away'):continue
   for t,opponent,y,advantage in ((h,a,int(r['outcome']=='home'),adv),(a,h,int(r['outcome']=='away'),-adv)):
    attenuation=g(rd[opponent]);p=1/(1+np.exp(-np.clip(q*attenuation*(strength[t]-strength[opponent]+advantage),-30,30)))
    precision[t]+=q*q*attenuation*attenuation*p*(1-p);gradient[t]+=q*attenuation*(y-p)
  # Shared-date outcomes only update latent strengths after all features exist.
  for t in precision:
   posterior=1/(rd[t]*rd[t])+precision[t];strength[t]+=gradient[t]/posterior;deviation[t]=np.sqrt(1/posterior);last[t]=d
 return [(r,x+extra[r['event_id']],n) for r,x,n in base],names

def build(rows,window=20,variant='baseline'):
 if variant.startswith('context_'):
  from .rest import adjusted_features
  built,names=build(rows,window,variant.removeprefix('context_'))
  return adjusted_features(built,names)
 if variant in ('rest_guard','no_rest'):
  from .rest import adjusted_features
  built,names=features(rows,window)
  return adjusted_features(built,names,'guard' if variant=='rest_guard' else 'no_rest')
 if variant=='bayesian':return bayesian_features(rows,window)
 if variant=='ratings':return rating_features(rows,window)
 if variant=='profile':return profile_features(rows,window)
 if variant=='form':return form_features(rows,window)
 if variant!='baseline':raise ValueError('Unknown research feature variant')
 return features(rows,window)

def definitions(league=None):
 result=[]
 for variant in ('baseline','form'):
  for window in (10,20,40):
   for c in (.03,.3):result.append({'kind':'logistic','window':window,'variant':variant,'c':c,'decay':False})
  for decay in (False,True):
   result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':decay})
  for leaves in (3,7):result.append({'kind':'boost','window':20,'variant':variant,'leaves':leaves,'decay':False})
 for variant in ('baseline','form'):
  for method in ('temperature','sigmoid'):
   result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':False,'calibrate':method})
  result.append({'kind':'boost','window':20,'variant':variant,'leaves':3,'decay':False,'calibrate':'temperature'})
  for weight in (.25,.5):result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':False,'elo_weight':weight})
 if league!='UFC':
  for window in (20,40):
   for c in (.03,.3):result.append({'kind':'logistic','window':window,'variant':'profile','c':c,'decay':False})
  for leaves in (3,7):result.append({'kind':'boost','window':20,'variant':'profile','leaves':leaves,'decay':False})
  for window in (10,20):result.append({'kind':'logistic','window':window,'variant':'profile','c':.1,'decay':True})
 for method in ('temperature','sigmoid'):
  result.append({'kind':'elo','window':20,'variant':'baseline','decay':False,'calibrate':method})
 for window in (10,20,40):
  for c in (.03,.3):result.append({'kind':'logistic','window':window,'variant':'ratings','c':c,'decay':False})
 for leaves in (3,7):result.append({'kind':'boost','window':20,'variant':'ratings','leaves':leaves,'decay':False})
 variants=('form','ratings') if league=='UFC' else ('form','profile','ratings')
 for variant in variants:
  for depth in (4,8):result.append({'kind':'extra_trees','window':20,'variant':variant,'depth':depth,'decay':False})
  for gamma in (.03,.1):result.append({'kind':'kernel','window':20,'variant':variant,'gamma':gamma,'c':.1,'decay':False})
  result.append({'kind':'ensemble','window':20,'variant':variant,'decay':False})
 for variant in ('form','ratings'):
  result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':True,'half_life_scale':.5})
  result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':False,'calibrate':'decision'})
 for variant in ('context_baseline','context_form','context_ratings'):
  for c in (.03,.3):result.append({'kind':'logistic','window':20,'variant':variant,'c':c,'decay':False})
  result.append({'kind':'boost','window':20,'variant':variant,'leaves':3,'decay':False})
 for c in (.03,.3):result.append({'kind':'logistic','window':20,'variant':'no_rest','c':c,'decay':False})
 for window in (10,20,40):
  for c in (.03,.3):result.append({'kind':'logistic','window':window,'variant':'context_bayesian','c':c,'decay':False})
 for leaves in (3,7):result.append({'kind':'boost','window':20,'variant':'context_bayesian','leaves':leaves,'decay':False})
 for gamma in (.03,.1):result.append({'kind':'kernel','window':20,'variant':'context_bayesian','gamma':gamma,'c':.1,'decay':False})
 result.append({'kind':'ensemble','window':20,'variant':'context_bayesian','decay':False})
 for variant in ('context_form','context_ratings','context_bayesian'):
  for alpha in (1.,10.):result.append({'kind':'neural','window':20,'variant':variant,'alpha':alpha,'decay':False})
  for depth in (4,8):result.append({'kind':'forest','window':20,'variant':variant,'depth':depth,'decay':False})
  result.append({'kind':'stack','window':20,'variant':variant,'decay':False})
  years=(3,6) if league=='UFC' else (4,8) if league in ('NFL','CFB') else (1,3) if league=='MLB' else (2,4)
  for horizon in years:result.append({'kind':'logistic','window':20,'variant':variant,'c':.1,'decay':False,'training_years':horizon})
 result.append({'kind':'bayesian_prior','window':20,'variant':'context_bayesian','decay':False})
 for method in ('temperature','sigmoid','decision'):result.append({'kind':'bayesian_prior','window':20,'variant':'context_bayesian','decay':False,'calibrate':method})
 if league!='UFC':
  for variant in ('context_form','context_bayesian'):
   for alpha in (1.,100.):
    for method in (None,'sigmoid'):result.append({'kind':'margin','window':20,'variant':variant,'ridge_alpha':alpha,'decay':False,**({'calibrate':method} if method else {})})
   for alpha in (.1,1.):
    for method in (None,'sigmoid'):result.append({'kind':'poisson','window':20,'variant':variant,'score_alpha':alpha,'decay':False,**({'calibrate':method} if method else {})})
 if league in ('UFC','MLB','NHL','NFL'):
  # Fixed sport-specific horizons: fight careers, football seasons, and shorter
  # baseball/hockey form. All retain the same minimum-history validation cohort.
  windows={'UFC':(3,5,8),'NFL':(5,8,16),'MLB':(5,15,60),'NHL':(5,15,30)}[league]
  for window in windows:
   for variant in ('context_form','context_bayesian'):
    for c in (.03,.3):result.append({'kind':'logistic','window':window,'variant':variant,'c':c,'decay':False})
  for variant in ('context_form','context_bayesian'):
   for kind,settings in (('neural',{'alpha':1.}),('forest',{'depth':8})):
    for method in ('temperature','sigmoid'):
     result.append(dict(kind=kind,window=20,variant=variant,decay=False,calibrate=method,calibration_refit=True,**settings))
 return result

class InsufficientCalibration(ValueError):pass

class ProbabilityBlend:
 def __init__(self,model,weight):self.model=model;self.weight=weight
 def predict_proba(self,X):
  p=(1-self.weight)*predict(self.model,X)+self.weight*elo(X)
  return np.column_stack((1-p,p))

class RestGuard:
 # Fit with the original rest input; validate the inference correction with
 # exactly the same weights. The final metadata column never enters prediction.
 def __init__(self,model):self.model=model
 def predict_proba(self,X):
  p=predict(self.model,X[:,:-1]);return np.column_stack((1-p,p))

class ModelAverage:
 def __init__(self,models):self.models=models
 def predict_proba(self,X):
  p=np.mean([predict(m,X) for m in self.models],axis=0)
  return np.column_stack((1-p,p))

class BayesianPrior:
 def predict_proba(self,X):
  from scipy.special import expit
  p=expit(X[:,-4]);return np.column_stack((1-p,p))

class MarginDistribution:
 def __init__(self,model,sigma):self.model=model;self.sigma=sigma
 def predict_proba(self,X):
  from scipy.special import ndtr
  p=np.clip(ndtr(self.model.predict(X)/self.sigma),1e-6,1-1e-6);return np.column_stack((1-p,p))

class ScoreDistribution:
 def __init__(self,home,away,maximum):self.home=home;self.away=away;self.maximum=maximum
 def predict_proba(self,X):
  from scipy.stats import skellam
  h=np.clip(self.home.predict(X),.05,self.maximum);a=np.clip(self.away.predict(X),.05,self.maximum)
  # Unresolved score ties receive equal eventual-winner probability; no draw
  # or bookmaker-settlement market is inferred from this auxiliary score model.
  p=np.clip(1-skellam.cdf(0,h,a)+.5*skellam.pmf(0,h,a),1e-6,1-1e-6)
  if not np.isfinite(p).all():raise ValueError('Scoring distribution produced nonfinite probabilities')
  return np.column_stack((1-p,p))

class TemporalStack:
 def __init__(self,models,meta,audit):self.models=models;self.meta=meta;self.calibration_audit=audit
 def predict_proba(self,X):
  from scipy.special import logit
  Z=np.column_stack([logit(np.clip(predict(m,X),1e-6,1-1e-6)) for m in self.models])
  return self.meta.predict_proba(Z)

class TemporalCalibration:
 def __init__(self,model,method,parameter,audit):self.model=model;self.method=method;self.parameter=parameter;self.calibration_audit=audit
 def predict_proba(self,X):
  from scipy.special import expit,logit
  z=logit(np.clip(predict(self.model,X),1e-6,1-1e-6))
  p=expit(z/self.parameter) if self.method=='temperature' else expit(z+self.parameter) if self.method=='decision' else self.parameter.predict_proba(z.reshape(-1,1))[:,1]
  return np.column_stack((1-p,p))

def quality_scores(y,p):
 result=scores(y,p);chosen=p>=.5;positive=y==1;negative=~positive
 result['precision']=float(y[chosen].mean()) if chosen.any() else None
 result['recall']=float(chosen[positive].mean()) if positive.any() else None
 result['balanced_accuracy']=float((chosen[positive].mean()+(~chosen[negative]).mean())/2) if positive.any() and negative.any() else None
 bins=np.minimum((np.clip(p,0,1)*10).astype(int),9);result['calibration_error']=float(sum(abs(p[bins==b].mean()-y[bins==b].mean())*(bins==b).sum() for b in range(10) if (bins==b).any())/len(y))
 return result

def uncertainty(y,incumbent,challenger,days):
 weeks=np.array([date.fromisoformat(d).strftime('%G-%V') for d in days]);unique=np.unique(weeks);rng=np.random.default_rng(42)
 old=np.clip(incumbent,1e-6,1-1e-6);new=np.clip(challenger,1e-6,1-1e-6)
 delta=-(y*np.log(new)+(1-y)*np.log(1-new))+(y*np.log(old)+(1-y)*np.log(1-old))
 accuracy=((challenger>=.5)==y).astype(float)-((incumbent>=.5)==y).astype(float)
 counts=np.array([(weeks==w).sum() for w in unique]);loss=np.array([delta[weeks==w].sum() for w in unique]);acc=np.array([accuracy[weeks==w].sum() for w in unique]);draws=rng.integers(0,len(unique),size=(1000,len(unique)));sizes=counts[draws].sum(axis=1)
 return {'log_loss_delta_95':np.quantile(loss[draws].sum(axis=1)/sizes,[.025,.975]).tolist(),'accuracy_gain_95':np.quantile(acc[draws].sum(axis=1)/sizes,[.025,.975]).tolist(),'calendar_weeks':len(unique),'note':'Descriptive weekly block intervals after candidate selection; selection uncertainty is not included. These are not independent promotion evidence.'}

def label(spec):
 return f"{spec['kind']}_{spec['variant']}_w{spec['window']}"+(f"_C{spec.get('c')}" if spec['kind']=='logistic' else f"_leaves{spec['leaves']}" if spec['kind']=='boost' else '')+(f"_depth{spec['depth']}" if spec['kind']=='extra_trees' else f"_gamma{spec['gamma']}" if spec['kind']=='kernel' else '')+('_recent'+str(spec.get('half_life_scale','')) if spec.get('decay') else '')+('_'+spec['calibrate'] if spec.get('calibrate') else '')+(f"_elo{spec['elo_weight']}" if spec.get('elo_weight') else '')+(f"_alpha{spec['alpha']}" if spec['kind']=='neural' else f"_depth{spec['depth']}" if spec['kind']=='forest' else '')+(f"_train{spec['training_years']}y" if spec.get('training_years') else '')+(f"_ridge{spec['ridge_alpha']}" if spec['kind']=='margin' else f"_scorealpha{spec['score_alpha']}" if spec['kind']=='poisson' else '')+('_refit' if spec.get('calibration_refit') else '')+('_legacy_rest_reference' if spec.get('diagnostic_only') else '')

def fit(spec,X,y,days,league,score_targets=None):
 if spec.get('training_years'):
  boundary=(date.fromisoformat(max(days))-timedelta(days=365*spec['training_years'])).isoformat();keep=np.array(days)>=boundary
  if keep.sum()<100 or len(set(y[keep]))<2:raise InsufficientCalibration('Recent training horizon has insufficient observations or classes')
  return fit({k:v for k,v in spec.items() if k!='training_years'},X[keep],y[keep],list(np.array(days)[keep]),league,None if score_targets is None else score_targets[keep])
 if spec['kind']=='stack':
  from scipy.special import logit
  unique=sorted(set(days));boundary=unique[int(len(unique)*.8)];ds=np.array(days);inner=ds<boundary;cal=~inner
  if inner.sum()<80 or cal.sum()<30 or len(set(y[inner]))<2 or len(set(y[cal]))<2:raise InsufficientCalibration('Inner chronological stacking block has insufficient observations or classes')
  common={k:v for k,v in spec.items() if k!='kind'}
  models=[fit(dict(common,kind='logistic',c=.1),X[inner],y[inner],list(ds[inner]),league),fit(dict(common,kind='boost',leaves=3),X[inner],y[inner],list(ds[inner]),league),fit(dict(common,kind='extra_trees',depth=8),X[inner],y[inner],list(ds[inner]),league)]
  Z=np.column_stack([logit(np.clip(predict(m,X[cal]),1e-6,1-1e-6)) for m in models])
  meta=make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=500,random_state=42));meta.fit(Z,y[cal])
  audit={'base_train_end':str(max(ds[inner])),'calibration_start':str(min(ds[cal])),'calibration_end':str(max(ds[cal])),'calibration_n':int(cal.sum()),'method':'temporal stacking'}
  return TemporalStack(models,meta,audit)
 if spec.get('variant')=='rest_guard':
  original=X[:,:-1].copy();original[:,4]=X[:,-1]
  if not spec.get('guard_legacy'):
   base={k:v for k,v in spec.items() if k!='guard_legacy'};base['variant']='baseline';m=fit(base,original,y,days,league)
  elif spec['kind']=='elo':m=None
  else:
   from .model import estimator
   kind='boost' if spec['kind']=='boost' else 'logistic_strong' if spec.get('c')==.01 else 'logistic_weak' if spec.get('c')==1 else 'logistic'
   m=estimator(kind);m.fit(original,y)
  return RestGuard(m)
 if spec.get('calibrate'):
  from scipy.optimize import minimize_scalar
  from scipy.special import expit,logit
  unique=sorted(set(days));boundary=unique[int(len(unique)*.8)];ds=np.array(days);inner=ds<boundary;cal=~inner
  if inner.sum()<80 or cal.sum()<30 or len(set(y[inner]))<2 or len(set(y[cal]))<2:raise InsufficientCalibration('Inner chronological calibration block has insufficient observations or classes')
  base={k:v for k,v in spec.items() if k not in ('calibrate','calibration_refit')};model=fit(base,X[inner],y[inner],list(ds[inner]),league,None if score_targets is None else score_targets[inner]);z=logit(np.clip(predict(model,X[cal]),1e-6,1-1e-6))
  if spec['calibrate']=='temperature':
   objective=lambda t:float(np.mean(np.logaddexp(0,z/t)-y[cal]*z/t))
   optimum=minimize_scalar(objective,bounds=(.75,3.),method='bounded');parameter=float(optimum.x)
  elif spec['calibrate']=='decision':
   # Tune the decision boundary only inside the training fold, while keeping
   # calibration-block log loss and Brier no worse than the unshifted model.
   original=quality_scores(y[cal],expit(z));options=[]
   for offset in np.linspace(-.4,.4,33):
    q=quality_scores(y[cal],expit(z+offset))
    if q['log_loss']<=original['log_loss']+1e-12 and q['brier']<=original['brier']+1e-12:options.append((q['accuracy'],-q['log_loss'],-abs(offset),float(offset)))
   parameter=max(options)[-1]
  else:
   parameter=LogisticRegression(C=.1,max_iter=500,random_state=42);parameter.fit(z.reshape(-1,1),y[cal])
  audit={'base_train_end':str(max(ds[inner])),'calibration_start':str(min(ds[cal])),'calibration_end':str(max(ds[cal])),'calibration_n':int(cal.sum()),'method':spec['calibrate']}
  if spec.get('calibration_refit'):
   # Freeze calibration learned from out-of-time inner predictions, then refit
   # the predictor on all outer-training rows. Outer validation stays unseen.
   model=fit(base,X,y,days,league,score_targets)
   audit['refit_through']=str(max(days));audit['refit_n']=len(y)
  return TemporalCalibration(model,spec['calibrate'],parameter,audit)
 if spec.get('elo_weight'):
  base={k:v for k,v in spec.items() if k!='elo_weight'}
  return ProbabilityBlend(fit(base,X,y,days,league),spec['elo_weight'])
 if spec['kind']=='bayesian_prior':return BayesianPrior()
 if spec['kind']=='elo':return None
 if spec['kind']=='ensemble':
  common={k:v for k,v in spec.items() if k!='kind'}
  return ModelAverage([fit(dict(common,kind='logistic',c=.1),X,y,days,league),fit(dict(common,kind='boost',leaves=3),X,y,days,league),fit(dict(common,kind='extra_trees',depth=8),X,y,days,league)])
 weights=None
 if spec.get('decay'):
  latest=date.fromisoformat(max(days));age=np.array([(latest-date.fromisoformat(d)).days for d in days]);weights=np.exp2(-age/(HALF_LIFE[league]*spec.get('half_life_scale',1)))
 if spec['kind'] in ('margin','poisson'):
  if league=='UFC':raise ValueError('Fight outcome encodings are not physical score targets')
  if score_targets is None or score_targets.shape!=(len(y),2) or not np.isfinite(score_targets).all() or (score_targets<0).any():raise ValueError('Scoring models require complete nonnegative training-only score targets')
  if spec['kind']=='margin':
   target=score_targets[:,0]-score_targets[:,1];m=make_pipeline(StandardScaler(),Ridge(alpha=spec.get('ridge_alpha',1.)));kwargs={'ridge__sample_weight':weights} if weights is not None else {};m.fit(X,target,**kwargs)
   sigma=max(.5,float(np.sqrt(np.mean((target-m.predict(X))**2))));return MarginDistribution(m,sigma)
  models=[]
  for side in (0,1):
   m=make_pipeline(StandardScaler(),PoissonRegressor(alpha=spec.get('score_alpha',.1),max_iter=300,tol=1e-4));kwargs={'poissonregressor__sample_weight':weights} if weights is not None else {};m.fit(X,score_targets[:,side],**kwargs);models.append(m)
  return ScoreDistribution(*models,maximum={'NBA':250,'WNBA':200,'NFL':100,'CFB':150,'NHL':30,'MLB':60}[league])
 if spec['kind']=='boost':
  m=HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=spec.get('leaves',7),l2_regularization=20,learning_rate=.04,random_state=42);m.fit(X,y,sample_weight=weights)
 elif spec['kind']=='extra_trees':
  m=ExtraTreesClassifier(n_estimators=120,max_depth=spec.get('depth',8),min_samples_leaf=20,max_features=1.,n_jobs=1,random_state=42);m.fit(X,y,sample_weight=weights)
 elif spec['kind']=='forest':
  m=RandomForestClassifier(n_estimators=160,max_depth=spec.get('depth',8),min_samples_leaf=15,max_features=.8,n_jobs=1,random_state=42);m.fit(X,y,sample_weight=weights)
 elif spec['kind']=='neural':
  m=make_pipeline(StandardScaler(),MLPClassifier(hidden_layer_sizes=(16,),alpha=spec.get('alpha',1.),max_iter=250,learning_rate_init=.003,tol=.001,n_iter_no_change=15,early_stopping=False,random_state=42));kwargs={'mlpclassifier__sample_weight':weights} if weights is not None else {};m.fit(X,y,**kwargs)
 elif spec['kind']=='kernel':
  m=make_pipeline(StandardScaler(),Nystroem(kernel='rbf',gamma=spec.get('gamma',.1),n_components=min(64,len(y)),random_state=42),LogisticRegression(C=spec.get('c',.1),max_iter=800,random_state=42));kwargs={'logisticregression__sample_weight':weights} if weights is not None else {};m.fit(X,y,**kwargs)
 else:
  m=make_pipeline(StandardScaler(),LogisticRegression(C=spec.get('c',.1),max_iter=800,random_state=42));kwargs={'logisticregression__sample_weight':weights} if weights is not None else {};m.fit(X,y,**kwargs)
 return m

def predict(m,X):return elo(X) if m is None else m.predict_proba(X)[:,1]

def incumbent_spec(report,champion=None):
 if champion and champion.get('research_spec'):return dict(champion['research_spec'])
 selected=report['selected'];parts=selected.split('_w');window=int(parts[-1].split('_')[0]);kind='elo' if selected.startswith('elo') else 'boost' if selected.startswith('boost') else 'logistic'
 return {'kind':kind,'window':window,'variant':'baseline','c':.01 if 'strong' in selected else 1. if 'weak' in selected else .1,'leaves':7,'decay':False,'legacy':True}

def review(rows,report,champion=None):
 """Compare on identical expanding development dates; return a deployable challenger."""
 rows=[r for r in rows if r['outcome'] in ('home','away')];league=report['league'];cut=report['final_test_start'];dev=[r for r in rows if r['date']<cut]
 days=sorted({r['date'] for r in dev})
 if len(dev)<200 or len(days)<40:raise ValueError('Not enough pre-test development history for a comparable review')
 # Every contender uses these exact date blocks and the same warm-up cohort.
 folds=[]
 for left,right in ((.4,.6),(.6,.8),(.8,1.0)):
  start=days[int(len(days)*left)];end=days[int(len(days)*right)] if right<1 else cut;folds.append((start,end))
 reference_spec=incumbent_spec(report,champion);inc_spec=reference_spec
 if reference_spec['variant']=='baseline':inc_spec=dict(reference_spec,variant='rest_guard',legacy=False,guard_legacy=reference_spec.get('legacy',False))
 specs=[inc_spec,*definitions(league)]
 if reference_spec['variant']=='baseline':specs.append(dict(reference_spec,diagnostic_only=True))
 cache={};results=[];predictions=[];ds=np.array([r['date'] for r in dev]);y=np.array([int(r['outcome']=='home') for r in dev]);min_history=3 if league=='UFC' else 5
 score_targets=np.array([[float(r['home_score']),float(r['away_score'])] for r in dev])
 for spec in specs:
  key=(spec['window'],spec['variant'])
  if key not in cache:cache[key]=build(dev,*key)
 cohort=np.logical_and.reduce([np.array([v[2]>=min_history for v in built]) for built,_ in cache.values()])
 # A sparse-history sport may need a later common start for inner calibration.
 # This uses training sample/class availability only, never validation scores.
 fold_policy='Original shared 40/60/80 percent expanding date folds'
 first_index=int(len(days)*.4)
 for index in range(first_index,len(days)):
  tr=(ds<days[index])&cohort;td=sorted(set(ds[tr]))
  if len(td)<2:continue
  boundary=td[int(len(td)*.8)];inner=tr&(ds<boundary);cal=tr&(ds>=boundary)
  if inner.sum()>=80 and cal.sum()>=30 and len(set(y[inner]))==2 and len(set(y[cal]))==2:break
 else:index=first_index
 if index>first_index:
  indices=[index+(len(days)-index)*i//3 for i in range(3)]
  proposed=[(days[ix],days[indices[i+1]] if i<2 else cut) for i,ix in enumerate(indices)]
  if all(((ds>=start)&(ds<end)&cohort).sum()>=20 for start,end in proposed):
   folds=proposed;fold_policy='Shared folds start after sufficient training-only history for 80 base and 30 calibration observations with both classes; no validation scores determine dates'
 for i,spec in enumerate(specs):
  built,names=cache[(spec['window'],spec['variant'])];X=np.array([v[1] for v in built]);evalX=X
  if spec['variant'] not in ('rest_guard','no_rest') and not spec['variant'].startswith('context_') and not spec.get('diagnostic_only'):
   from .rest import adjusted_features
   corrected,_=adjusted_features(built,names,'recovery_only');evalX=np.array([v[1] for v in corrected])
  blocks=[];p_all=[];y_all=[];d_all=[];failure=None
  for start,end in folds:
   tr=(ds<start)&cohort;va=(ds>=start)&(ds<end)&cohort
   if va.sum()<20 or len(set(y[tr]))<2:raise ValueError('An expanding fold lacks sufficient comparable observations')
   if spec.get('legacy') and spec['kind']!='elo':
    from .model import estimator
    kind='boost' if spec['kind']=='boost' else 'logistic_strong' if spec['c']==.01 else 'logistic_weak' if spec['c']==1 else 'logistic';m=estimator(kind);m.fit(X[tr],y[tr])
   else:
    try:m=fit(spec,X[tr],y[tr],list(ds[tr]),league,score_targets[tr])
    except InsufficientCalibration as e:failure=str(e);break
   p=predict(m,evalX[va]);blocks.append(dict(quality_scores(y[va],p),train_end=str(max(ds[tr])),validation_start=str(min(ds[va])),validation_end=str(max(ds[va]))));p_all.extend(p);y_all.extend(y[va]);d_all.extend(ds[va])
   if hasattr(m,'calibration_audit'):blocks[-1]['calibration']=m.calibration_audit
  if failure:
   results.append({'name':label(spec),'specification':spec,'folds':blocks,'validation':None,'status':'skipped','reason':failure});predictions.append(None);continue
  aggregate=quality_scores(np.array(y_all),np.array(p_all));results.append({'name':champion.get('selected',report['selected']) if i==0 and champion else report['selected'] if i==0 else label(spec),'specification':spec,'folds':blocks,'status':'completed','validation':aggregate});predictions.append((np.array(y_all),np.array(p_all),d_all))
 incumbent=results[0];eligible=[i for i,r in enumerate(results[1:],1) if not r['specification'].get('diagnostic_only') and r['validation'] is not None and r['validation']['accuracy']>=incumbent['validation']['accuracy'] and r['validation']['brier']<=incumbent['validation']['brier']]
 eligible=[i for i in eligible if results[i]['validation']['log_loss']<incumbent['validation']['log_loss']]
 selected=max(eligible,key=lambda i:(results[i]['validation']['accuracy'],-results[i]['validation']['log_loss'])) if eligible else 0
 accuracy_leader=max((r for r in results if r['validation'] is not None and not r['specification'].get('diagnostic_only')),key=lambda r:(r['validation']['accuracy'],-r['validation']['log_loss']))
 if results[selected]['validation']['log_loss']>=incumbent['validation']['log_loss']:selected=0
 chosen=results[selected];spec=chosen['specification'];built,names=build(rows,spec['window'],spec['variant']);warm=np.array([v[2]>=min_history for v in built]);X=np.array([v[1] for v in built]);yy=np.array([int(v[0]['outcome']=='home') for v in built]);all_days=np.array([v[0]['date'] for v in built])
 fit_failure=None
 try:
  if spec.get('legacy') and spec['kind']!='elo':
   from .model import estimator
   kind='boost' if spec['kind']=='boost' else 'logistic_strong' if spec['c']==.01 else 'logistic_weak' if spec['c']==1 else 'logistic';m=estimator(kind);m.fit(X[warm],yy[warm])
  else:m=fit(spec,X[warm],yy[warm],list(all_days[warm]),league,np.array([[float(r['home_score']),float(r['away_score'])] for r in rows])[warm])
 except InsufficientCalibration as e:fit_failure=str(e)
 artifact=None if fit_failure else {'model':m,'research_spec':dict(spec),'window':spec['window'],'variant':spec['variant'],'extra':False,'names':names,'digest':version(rows),'training_event_ids':[r['event_id'] for r in rows],'last_date':rows[-1]['date'],'league':league,'neutral_variation':len(np.unique(X[warm,1]))>1,'selected':chosen['name'],'refitted':now()}
 result={'version':VERSION,'checked':now(),'fit_status':'unavailable' if fit_failure else 'ready','fit_error':fit_failure,'fit_dataset_sha256':version(rows),'league':league,'development_sha256':version(dev),'development_through':dev[-1]['date'],'excluded_final_test_from':cut,'selected':chosen['name'],'incumbent':incumbent,'best':chosen,'accuracy_leader':accuracy_leader,'rest_policy_review':{'before':next(r for r in results if r['specification'].get('diagnostic_only')),'after':incumbent} if any(r['specification'].get('diagnostic_only') for r in results) else None,'selection_objective':'Highest development winner accuracy among candidates with lower log loss and non-worse Brier than the incumbent; ties use lower log loss. Independent prospective promotion checks still apply.','candidates':results,'fold_policy':fold_policy,'candidate_count':sum(not r['specification'].get('diagnostic_only') for r in results[1:]),'completed_candidates':sum(r['status']=='completed' and not r['specification'].get('diagnostic_only') for r in results[1:]),'comparison_uncertainty':uncertainty(predictions[selected][0],predictions[0][1],predictions[selected][1],predictions[selected][2]),'accuracy_gain':chosen['validation']['accuracy']-incumbent['validation']['accuracy'],'log_loss_gain':incumbent['validation']['log_loss']-chosen['validation']['log_loss'],'status':'challenger identified' if selected else 'incumbent specification retained','note':'Expanding development backtests only. Candidate selection gains are optimistic; no new independent test or production improvement is claimed. Original final-test dates were excluded. Production promotion still requires the separate prospective loss-review gate.'}
 return artifact,result

def saved_review(root,rows,report,champion=None):
 root=Path(root);root.mkdir(parents=True,exist_ok=True);path=root/'research-review.json';fingerprint=hashlib.sha256((VERSION+version([r for r in rows if r['date']<report['final_test_start']])+json.dumps(incumbent_spec(report,champion),sort_keys=True)).encode()).hexdigest()
 if path.exists():
  prior=json.loads(path.read_text())
  if prior.get('fingerprint')==fingerprint and (prior.get('fit_status')=='ready' or prior.get('fit_dataset_sha256')==version(rows)):return prior
 artifact,result=review(rows,report,champion);result['fingerprint']=fingerprint
 if path.exists():
  previous=json.loads(path.read_text());folds=lambda r:[(f['validation_start'],f['validation_end'],f['n']) for f in r['incumbent']['folds']]
  if previous.get('development_sha256')==result['development_sha256'] and folds(previous)==folds(result):
   result['previous_search']={'version':previous['version'],'name':previous['best']['name'],'validation':previous['best']['validation'],'accuracy_gain':result['best']['validation']['accuracy']-previous['best']['validation']['accuracy'],'note':'Same development data and chronological validation games; search-selection optimism remains.'}

 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,allow_nan=False));temporary.replace(path)
 if artifact is not None:joblib.dump(artifact,root/'research-challenger.joblib')
 else:(root/'research-challenger.joblib').unlink(missing_ok=True)
 return result
