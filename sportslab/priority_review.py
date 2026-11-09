"""Exploratory monitoring and fixed calibration comparisons of saved predictions.

No retrospective refitting of the winner models and no production promotion.
"""
from collections import defaultdict
import math
from .grading import identity,team

PRIORITIES={'NFL':1,'NBA':2,'NHL':3}

def metrics(rows,probabilities=None):
 if not rows:return None
 p=probabilities if probabilities is not None else [r['home_probability'] for r in rows]
 y=[int(r['outcome']=='home') for r in rows]
 return {'n':len(rows),'accuracy':sum((a>=.5)==bool(b) for a,b in zip(p,y))/len(rows),'log_loss':sum(-math.log(max(1e-12,a if b else 1-a)) for a,b in zip(p,y))/len(rows),'brier':sum((a-b)**2 for a,b in zip(p,y))/len(rows)}

def calibrated(p,temperature,offset):
 p=max(1e-8,min(1-1e-8,p));z=(math.log(p/(1-p))+offset)/temperature
 return 1/(1+math.exp(-max(-30,min(30,z))))

def review(league,archive,injury_research):
 if league not in PRIORITIES:return None
 unique={}
 for p in sorted(archive,key=lambda r:r['generated_at']):
  if p.get('result_status')=='not_pregame':continue
  unique.setdefault((identity(p['id']),team(p['home']),team(p['away'])),p)
 rows=sorted([p for p in unique.values() if isinstance(p.get('correct'),bool) and p.get('outcome') in ('home','away')],key=lambda r:(r['date'],r['id']))
 bands=[]
 for lo,hi in ((.5,.6),(.6,.7),(.7,.8),(.8,1.01)):
  group=[r for r in rows if lo<=max(r['home_probability'],1-r['home_probability'])<hi]
  if group:bands.append({'from':lo,'to':min(1,hi),'mean_confidence':sum(max(r['home_probability'],1-r['home_probability']) for r in group)/len(group),**metrics(group)})
 teams=defaultdict(list)
 for r in rows:
  for side in ('home','away'):teams[r[side]].append(r)
 problems=sorted([{'team':name,**metrics(group)} for name,group in teams.items() if len(group)>=3],key=lambda r:(-r['log_loss'],-r['n']))[:5]
 result={'priority':PRIORITIES[league],'league':league,'saved_predictions':metrics(rows),'confidence_bands':bands,'teams_to_review':problems,'injury_observations':injury_research.get('settled',0),'injury_minimum':injury_research.get('minimum_settled',200),'injury_adjustment_approved':False,'production_changed':False,'calibration_review':{'status':'insufficient saved history'},'findings':[],'note':'Exploratory analysis of original saved pregame predictions. Small samples and repeated monitoring limit conclusions. No live model is changed; independent prospective promotion gates still apply.'}
 if not rows:return result
 result['findings'].append('Winner accuracy is evaluated alongside log loss and Brier; confidently wrong picks receive greater probability-loss penalties.')
 for band in bands:
  if band['n']>=10 and band['mean_confidence']-band['accuracy']>.08:result['findings'].append(f"The {int(band['from']*100)}–{int(band['to']*100)}% confidence band is overconfident in this sample ({band['n']} games); investigate calibration before increasing confidence.")
 if result['injury_observations']<result['injury_minimum']:result['findings'].append('Injury data are still below the research sample requirement; a numerical injury effect cannot yet be supported.')
 days=sorted({r['date'] for r in rows})
 if len(rows)<30 or len(days)<9:return result
 cutoff=days[len(days)*2//3];development=[r for r in rows if r['date']<cutoff];check=[r for r in rows if r['date']>=cutoff]
 if len(development)<20 or len(check)<10:return result
 base=metrics(development);candidates=[]
 for temperature in (.8,1.,1.2,1.5,2.):
  for offset in (-.1,0.,.1):
   score=metrics(development,[calibrated(r['home_probability'],temperature,offset) for r in development]);candidates.append({'temperature':temperature,'offset':offset,'development':score})
 eligible=[c for c in candidates if c['development']['accuracy']>=base['accuracy'] and c['development']['brier']<=base['brier'] and c['development']['log_loss']<base['log_loss']-1e-9]
 best=max(eligible,key=lambda c:(c['development']['accuracy'],-c['development']['log_loss'])) if eligible else {'temperature':1.,'offset':0.,'development':base}
 old=metrics(check);new=metrics(check,[calibrated(r['home_probability'],best['temperature'],best['offset']) for r in check]);passed=best['temperature']!=1. or best['offset']!=0.
 passed=passed and new['accuracy']>=old['accuracy'] and new['log_loss']<=old['log_loss']-.002 and new['brier']<=old['brier']
 if not passed and (best['temperature']!=1. or best['offset']!=0.):result['findings'].append('The development-selected calibration failed the later accuracy/probability-quality check. Retain the original probabilities; do not apply blanket confidence changes.')
 result['calibration_review']={'status':'promising exploratory calibration' if passed else 'retain existing probabilities','candidate_count':len(candidates),'development_through':development[-1]['date'],'check_from':cutoff,'selected':best,'baseline_check':old,'candidate_check':new,'passes_chronological_check':bool(passed),'promotion_allowed':False,'note':'Fixed temperature and home-bias grid selected only on earlier saved results, then checked on later saved results. This is exploratory calibration research, not a newly independent prospective test or a winner-model refit.'}
 return result
