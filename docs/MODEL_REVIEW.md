# Model quality review — October 22, 2026

The review compares 40 candidates per team sport and 32 for UFC. All candidates completed on the current common development folds. The catalog adds nested chronological probability calibration, fixed Elo blends and team scoring profiles. Original final-test dates stay excluded.

| Sport | Incumbent accuracy | Selected accuracy | Incumbent log loss | Selected log loss | Selected specification |
|---|---:|---:|---:|---:|---|
| NBA | 68.50% | 68.79% | 0.587246 | 0.586174 | logistic_form_w40_C0.3 |
| NFL | 63.79% | 63.90% | 0.633255 | 0.633254 | logistic_baseline_w10_C0.3 |
| NHL | 54.31% | 54.73% | 0.693590 | 0.691624 | logistic_baseline_w20_C0.03 |
| CFB | 73.19% | 73.19% | 0.555659 | 0.555312 | logistic_baseline_w20_C0.3 |
| WNBA | 68.34% | 68.34% | 0.610584 | 0.610584 | logistic_w10 |
| MLB | 55.52% | 55.75% | 0.682677 | 0.682457 | logistic_baseline_w40_C0.3 |
| UFC | 60.56% | 60.56% | 0.681635 | 0.679182 | elo_baseline_w20_temperature |

## What improved in this iteration

The six team-sport selections are unchanged from the preceding review: the new methods did not beat those selections while preserving the required accuracy and Brier performance.

UFC identified temperature-calibrated Elo. On the same 426 development validation fights, log loss decreased from 0.681635 to 0.679182, Brier from 0.244264 to 0.243054, and fixed-bin calibration error from 0.074315 to 0.064735. Accuracy remained 60.56%. The approximate paired weekly log-loss-difference interval was [-0.004841, -0.000026]; it does not account for candidate-selection optimism.

UFC’s shared first fold starts later because the earlier training data lacked sufficient usable fight history for calibration. The date decision uses training sample/class availability only. Consequently, these UFC percentages are not directly comparable with the preceding review’s different cohort. Every incumbent/challenger comparison above uses identical current validation dates and observations.

## Deployment boundary

These are development research results, not a new independent final test or a claim of live accuracy improvement. Production weights and already locked trials are preserved. A settled loss may open a trial of the revised candidate; replacement still requires the independent prospective promotion gate.

The public Model Lab includes calibration error, balanced accuracy, precision/recall, fold/calibration dates, candidate exclusions and descriptive weekly intervals. No injury, lineup or advanced player inputs were invented.
