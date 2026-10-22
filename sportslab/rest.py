"""Conservative schedule context, not medical recovery or player availability."""
from datetime import date
import math

VERSION='sport-rest-v1'
# Days between appearances, not full days off. Fixed before backtesting.
POLICIES={
 'NBA':{'typical_days':2,'recovery_cap_days':3,'inactive_after_days':21},
 'WNBA':{'typical_days':2,'recovery_cap_days':4,'inactive_after_days':28},
 'NHL':{'typical_days':2,'recovery_cap_days':4,'inactive_after_days':28},
 'NFL':{'typical_days':7,'recovery_cap_days':10,'inactive_after_days':35},
 'CFB':{'typical_days':7,'recovery_cap_days':10,'inactive_after_days':42},
 'MLB':{'typical_days':1,'recovery_cap_days':3,'inactive_after_days':14},
 'UFC':{'typical_days':90,'recovery_cap_days':180,'inactive_after_days':730},
}

def comparison(league,day,home_last,away_last):
 policy=POLICIES[league];d=date.fromisoformat(day)
 def gap(last):return (d-date.fromisoformat(last)).days if last else None
 h,a=gap(home_last),gap(away_last)
 reliable=all(v is not None and 0<v<=policy['inactive_after_days'] for v in (h,a))
 # A long gap can reflect offseason, injury, or missing coverage. Never award
 # recovery credit for it, or infer that the opponent is less rested.
 difference=(min(h,policy['recovery_cap_days'])-min(a,policy['recovery_cap_days'])) if reliable else 0.
 if league=='UFC':difference/=policy['typical_days']
 return dict(policy,version=VERSION,home_gap_days=h,away_gap_days=a,reliable_comparison=reliable,recovery_difference=float(difference),unit='90-day recovery intervals' if league=='UFC' else 'capped days between games',note='Recovery saturates at the sport-specific cap; long inactivity is not extra recovery.' if reliable else 'Rest advantage neutralized: missing history or long inactivity is not a verified recovery advantage. Inactivity is not a confirmed injury.')

def matchup_context(rows,league,day,home,away):
 last={}
 for r in rows:
  if r['date']<day and r['outcome'] in ('home','away'):
   for t in (r['home'],r['away']):
    if t in (home,away):last[t]=max(last.get(t,''),r['date'])
 return comparison(league,day,last.get(home),last.get(away))


def bounded_recovery(values,names,context):
 values=list(values);labels=list(names);values[4]=context['recovery_difference'];labels[4]='contextual_recovery_difference'
 if 'layoff_log_difference' in names:
  i=names.index('layoff_log_difference');cap=context['recovery_cap_days'];typical=context['typical_days']
  values[i]=(math.log1p(min(context['home_gap_days'],cap)/typical)-math.log1p(min(context['away_gap_days'],cap)/typical)) if context['reliable_comparison'] else 0.
  labels[i]='normalized_recovery_log_difference'
 return values,labels

def adjusted_features(built,names,mode='context'):
 """Transform after causal feature construction; query rows never update history."""
 last={};out=[];group=[];current=None
 def emit(items):
  for r,x,n in items:
   c=comparison(r['league'],r['date'],last.get(r['home']),last.get(r['away']));original=x[4];values,_=bounded_recovery(x,names,c)
   if mode=='no_rest':values[4]=0.
   if mode=='context':
    inactive=lambda v:int(v is not None and v>c['inactive_after_days'])
    values.extend([inactive(c['home_gap_days'])-inactive(c['away_gap_days']),int(c['home_gap_days'] is None or c['away_gap_days'] is None)])
   if mode=='guard':values.append(original)
   out.append((r,values,n))
  for r,_,_ in items:
   if r['outcome'] in ('home','away'):
    last[r['home']]=r['date'];last[r['away']]=r['date']
 for item in built:
  if current is not None and item[0]['date']!=current:emit(group);group=[]
  current=item[0]['date'];group.append(item)
 if group:emit(group)
 labels=list(names);labels[4]='contextual_recovery_difference' if mode!='no_rest' else 'rest_excluded'
 if 'layoff_log_difference' in labels:labels[labels.index('layoff_log_difference')]='normalized_recovery_log_difference'
 if mode=='context':
  labels.extend(['long_inactivity_difference','rest_history_missing'])
 if mode=='guard':labels.append('legacy_rest_training_only')
 return out,labels
