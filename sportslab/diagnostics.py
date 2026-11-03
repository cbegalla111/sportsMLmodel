"""Descriptive monitoring from immutable saved forecasts, never causal loss attribution."""
from collections import defaultdict
from datetime import date
import numpy as np
from .model import scores

def analyze(entries):
 rows=sorted([e for e in entries if e.get('settled') and e.get('outcome') in ('home','away')],key=lambda e:(e['date'],e['id']))
 if not rows:return {'n':0,'rolling':[],'teams':[],'venues':[],'drift':{'status':'insufficient evidence'},'actions':[],'calibration':None}
 def evaluate(group):
  y=np.array([int(e['outcome']=='home') for e in group]);p=np.array([e['home_probability'] for e in group]);s=scores(y,p)
  confidence=np.maximum(p,1-p);correct=(p>=.5)==y
  s.update(mean_confidence=float(confidence.mean()),confidence_gap=float(confidence.mean()-correct.mean()),high_confidence_misses=int(((confidence>=.75)&~correct).sum()))
  return s
 rolling=[dict(window=n,**evaluate(rows[-n:])) for n in (10,25,50,100) if len(rows)>=n]
 teams=defaultdict(list);venues=defaultdict(list)
 for r in rows:
  for side in ('home','away'):teams[r[side]].append(r)
  venues['home favorite' if r['home_probability']>=.5 else 'away favorite'].append(r)
 team_scores=[dict(team=t,**evaluate(g)) for t,g in teams.items() if len(g)>=3]
 team_scores.sort(key=lambda r:(-r['log_loss'],-r['n'],r['team']))
 drift={'status':'insufficient evidence','minimum_results':100,'note':'Compare the latest 50 saved picks with the preceding 50; this is monitoring, not permission to retune a live model.'}
 if len(rows)>=100:
  before,after=rows[-100:-50],rows[-50:];old,new=evaluate(before),evaluate(after)
  blocks=defaultdict(list)
  for index,group in enumerate((before,after)):
   for r in group:
    p=np.clip(r['home_probability'],1e-6,1-1e-6);y=int(r['outcome']=='home');loss=-(y*np.log(p)+(1-y)*np.log1p(-p));week=date.fromisoformat(r['date']).strftime('%G-%V');blocks[week].append((index,float(loss)))
  unique=list(blocks);interval=None
  if len(unique)>=8:
   rng=np.random.default_rng(42);changes=[]
   for draw in rng.integers(0,len(unique),size=(500,len(unique))):
    samples=[v for i in draw for v in blocks[unique[i]]];a=[v for i,v in samples if i==0];b=[v for i,v in samples if i==1]
    if a and b:changes.append(float(np.mean(b)-np.mean(a)))
   if len(changes)>=400:interval=np.quantile(changes,[.025,.975]).tolist()
  delta=new['log_loss']-old['log_loss'];drift.update(status='deterioration signal' if interval and interval[0]>0 else 'watch' if delta>.03 else 'no clear deterioration',previous=old,recent=new,log_loss_change=delta,weekly_log_loss_change_95=interval,weeks=len(unique))
 all_scores=evaluate(rows);p=np.array([r['home_probability'] for r in rows]);y=np.array([int(r['outcome']=='home') for r in rows]);bins=np.minimum((np.clip(p,0,1)*10).astype(int),9);reliability=resolution=0.;base=float(y.mean());ece=0.
 for b in range(10):
  ix=bins==b
  if ix.any():
   weight=float(ix.mean());observed=float(y[ix].mean());predicted=float(p[ix].mean());reliability+=weight*(predicted-observed)**2;resolution+=weight*(observed-base)**2;ece+=weight*abs(predicted-observed)
 actions=[]
 if all_scores['confidence_gap']>.05:actions.append('Review overconfidence using chronological calibration challengers; a confidence gap is descriptive, not proof of a cause.')
 if all_scores['high_confidence_misses']:actions.append('Inspect high-confidence misses and reported player availability; do not assume an injury caused a loss.')
 if drift['status'] in ('watch','deterioration signal'):actions.append('Investigate changing form or data coverage and evaluate a frozen adaptive challenger on new dates.')
 if len(rows)<100:actions.append('Collect more pregame evidence before drawing strong conclusions or promoting a challenger.')
 return {'n':len(rows),'rolling':rolling,'teams':team_scores[:12],'venues':[dict(group=k,**evaluate(v)) for k,v in sorted(venues.items())],'drift':drift,'actions':actions,'calibration':{'expected_calibration_error':float(ece),'binned_reliability':float(reliability),'binned_resolution':float(resolution),'outcome_uncertainty':base*(1-base),'binning_residual':float(all_scores['brier']-(reliability-resolution+base*(1-base))),'note':'Binned reliability and resolution are descriptive. The residual reflects within-bin variation; this is not an exact individual-probability Brier decomposition.'},'note':'Uses only actually saved, settled predictions. Team summaries count a game for both teams and must not be summed as independent games. Drift comparisons are observational; schedule difficulty and small samples can change scores.'}
