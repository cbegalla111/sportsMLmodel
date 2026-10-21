# Seven-sport model backtest review

Reviewed October 21, 2026. Each sport compares 20 challengers against its incumbent specification on three chronological development folds. The original final-test dates are excluded. These are candidate-selection results, not independent test scores or proven production gains.

| Sport | Incumbent accuracy | Selected accuracy | Log-loss reduction | Selected specification |
|---|---:|---:|---:|---|
| NBA | 68.50% | 68.79% | 0.001072 | logistic_form_w40_C0.3 |
| NFL | 63.79% | 63.90% | 0.000001 | logistic_baseline_w10_C0.3 |
| NHL | 54.31% | 54.73% | 0.001966 | logistic_baseline_w20_C0.03 |
| CFB | 73.19% | 73.19% | 0.000347 | logistic_baseline_w20_C0.3 |
| WNBA | 68.34% | 68.34% | 0.000000 | logistic_w10 |
| MLB | 55.52% | 55.75% | 0.000221 | logistic_baseline_w40_C0.3 |
| UFC | 60.45% | 60.45% | 0.000000 | elo_w20 |

Selected challengers cannot worsen development accuracy or Brier; lower log loss selects among eligible candidates. Small differences may be noise, especially after comparing many candidates. Every candidate and fold is visible in the public Model Lab.

Production weights are retained until the loss-triggered independent confirmation gate passes. No champion promotion is claimed by this review. Richer challengers are fitted and ready for a prospective trial when a settled miss opens one. Existing locked trials are preserved.

New inputs use only prior result history: short form, opponent strength, opponent-adjusted form, volatility, recent workload, layoffs and experience. Recency weighting and 10/20/40-appearance windows are compared. There are no invented injury, lineup or advanced player statistics.
