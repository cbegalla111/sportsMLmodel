"""Faithful local explanations: trained linear effects, never causal importance."""
import math
import numpy as np

DESCRIPTIONS={
 'elo_difference':('Team strength','Elo rating points','Home minus away historical Elo rating.'),
 'home_advantage':('Home venue','indicator','One for a home venue, zero for a neutral site. Constant home effects can be absorbed into the intercept.'),
 'win_rate_difference':('Recent win rate','fraction','Home minus away win fraction in the model’s trailing window.'),
 'scoring_margin_difference':('Recent scoring margin','score units','Home minus away average score margin in preceding games.'),
 'rest_difference':('Rest difference','days','Home minus away rest, bounded for the sport.'),
 'contextual_recovery_difference':('Sport-adjusted recovery','recovery units','Difference in bounded recovery; long layoffs do not earn unlimited rest credit.'),
 'uncertainty_adjusted_log_odds':('Strength adjusted for uncertainty','log odds','Relative team strength discounted for rating uncertainty.'),
 'adaptive_margin_strength_difference':('Outcome-adjusted scoring strength','score units','Strength updated from prior scoring surprises, before this game.'),
 'fast_surprise_difference':('Recent unexpected results','residual units','Recent wins and losses relative to prior expectations.'),
 'prediction_loss_difference':('Recent prediction errors','loss units','Difference in recent probability errors for the two opponents.'),
}

def describe(name):
 label,unit,description=DESCRIPTIONS.get(name,(name.replace('_',' ').capitalize(),'model units','A pregame historical input; inspect the raw value and training reference below.'))
 return {'label':label,'unit':unit,'description':description}

def explain(model,x,names,probability,home,away):
 unavailable={'status':'unavailable','note':'This model does not expose a verified additive contribution breakdown. Raw input values are shown without inventing importance scores.'}
 X=np.array([x],dtype=float);inner=model;count=len(names)
 if inner is not None and type(inner).__name__=='RestGuard':inner=inner.model;count-=1
 try:
  if inner is None:
   coefficients=np.zeros(len(names));coefficients[:2]=[math.log(10)/400,60*math.log(10)/400];reference=np.zeros(len(names));contributions=X[0]*coefficients;intercept=0.;method='elo_log_odds';baseline_note='Equal strength and neutral venue under the fixed Elo formula.'
  else:
   steps=getattr(inner,'steps',[])
   if len(steps)!=2:return unavailable
   scaler,regressor=steps[0][1],steps[1][1]
   if not all(hasattr(scaler,key) for key in ('mean_','scale_')) or not hasattr(regressor,'coef_') or list(regressor.classes_)!=[0,1]:return unavailable
   if len(scaler.mean_)!=count or regressor.coef_.shape!=(1,count):return unavailable
   reference=np.array(X[0],copy=True);reference[:count]=scaler.mean_
   coefficients=np.zeros(len(names));coefficients[:count]=regressor.coef_[0]/scaler.scale_
   contributions=(X[0]-reference)*coefficients;intercept=float(regressor.intercept_[0]);method='linear_log_odds';baseline_note='All active inputs set to their training averages; the intercept includes typical conditions already learned by the model.'
  sigmoid=lambda z:1/(1+math.exp(-max(-700,min(700,float(z)))))
  total_log_odds=intercept+sum(contributions);reconstructed=sigmoid(total_log_odds)
  if not math.isclose(reconstructed,probability,abs_tol=1e-8):return unavailable
  baseline=sigmoid(intercept);ranked=[]
  for i,name in enumerate(names):
   if name=='legacy_rest_training_only':continue
   other=sigmoid(total_log_odds-contributions[i]);effect=100*(probability-other)
   ranked.append({'factor':name,**describe(name),'input_value':float(X[0,i]),'reference_value':float(reference[i]),'log_odds_contribution':float(contributions[i]),'probability_effect_pp':effect,'probability_at_reference':other,'favors':home if effect>1e-9 else away if effect< -1e-9 else 'Neither'})
  ranked.sort(key=lambda f:abs(f['probability_effect_pp']),reverse=True)
  return {'status':'available','method':method,'baseline_probability':baseline,'baseline_note':baseline_note,'home_probability':probability,'intercept_log_odds':intercept,'ranked_factors':ranked,'note':'Effect = change in home-win probability when only this input moves from its reference value to its actual value, holding all other inputs fixed. Probability-point effects do not add up. Log-odds contributions plus the intercept do reconstruct the prediction. Correlated inputs can share information; these are model associations, not causes of the outcome.'}
 except (ValueError,TypeError,AttributeError,OverflowError):return unavailable
