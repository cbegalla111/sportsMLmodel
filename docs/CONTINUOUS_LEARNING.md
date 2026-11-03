# Continuous statistical improvement

The hourly workflow now combines immutable live-pick diagnostics, a bounded 21-specification adaptive research catalog per sport, and an additional independent challenger lane. It runs on NBA, NFL, NHL, MLB, CFB, WNBA and UFC. A separate modern NBA study uses the existing 2022–June 2025 development period. Winner-model inputs remain statistics-only; market prices are excluded.

## New methods

Seven additional causal signals describe adaptive latent strength, fast/slow unexpected results, surprise momentum, error variance, recent probability loss and normalized margins. State updates use `outcome - pregame estimate`, so an unexpected result produces a larger update than an expected win. Both wins and losses contribute. Adaptive step size responds to trailing error variance. All of a date's observations are computed before any outcomes on that date update adaptive state; this protects doubleheaders and shared-date fixtures. Team-season shrinkage is fixed beforehand. UFC has no artificial January season reset and no physical margin inferred from its 1–0 outcome encoding.

The fixed catalog contains twelve regularized logistic variants (10/20-game windows, three regularization levels, with/without sport-specific recency weighting), six inner-chronological calibration variants (temperature, sigmoid and constrained decision offset), and three probability blends with the core Bayesian features. These augment the existing Elo, uncertainty ratings, opponent-adjusted form, trees, neural nets, kernels, scoring models and NBA box-score research. This is a bounded study, not an assertion that all possible methods have been exhausted.

Compare the new catalog directly against the prior **development research winner**, not merely a weaker original baseline. All contenders share expanding validation dates and the same eligible games. A new candidate must improve log loss while preserving Brier score and winner accuracy against that prior winner. The original final-test period stays excluded. Inner calibration uses earlier training dates and disjoint later calibration dates, with outer validation unseen. Fitted coefficients and scales are learned inside the appropriate training partitions. Trial refits use the frozen specification on available training history; they do not select on future trial outcomes.

Search reports are cached by method catalog, development data hash, original test boundary, reference specification and prior research winner. Incoming post-development results do not repeatedly reselect hyperparameters on the same final test. New results update causal state and can inform frozen-specification refits after losses. `python -m scripts.research_adaptive` reproduces studies from verified runtime public history; when WNBA/UFC champion files are absent, checked-in public metadata can support an offline specification comparison only if the original champion remains unchanged. No private uploads or credentials enter that study.

## Automatic loss loop

1. Import finals and settle the first saved pregame predictions under their actual policy.
2. Compute rolling probability and winner-error diagnostics.
3. Reuse or refresh bounded chronological development studies when their fingerprint changes.
4. After a saved loss, lock an additional qualifying adaptive challenger and a frozen reference. Keep ongoing trials and their weights intact.
5. Compare only subsequent dates against the exact frozen reference. **Results must occur after both the training cutoff and the trial's actual creation date.** This closes a timing loophole where late-imported already-played games could otherwise count as future evidence. Same-day ordering cannot be proven with date-grouped replay, so the lock date is conservatively excluded. Existing trial weights and original saved picks remain unchanged.
6. Require the existing gate: at least 100 new results across eight calendar weeks; log-loss gain at least .002; non-worse Brier and winner accuracy; paired weekly bootstrap 95% log-loss delta wholly below zero.
7. Preserve the old champion and archive superseded trials if the challenger passes. A reference checksum change invalidates its shadow trial. A failed challenger never overwrites live weights; a later real loss may start a new independently evaluated attempt.

The adaptive lane is separate from the existing primary and NBA feedback trials. It can promote only through the same strict gate. An hourly refresh is not a promise of an hourly model change. Production performance can stay flat or deteriorate, and no learning system can guarantee continuing gains.

## Better assessment of losses

Diagnostics score only actually saved, settled decisive outcomes:

- Last 10/25/50/100 picks: accuracy, log loss, Brier, mean favorite confidence, confidence-minus-accuracy gap and high-confidence misses.
- Per-team and home/away-favorite summaries. Team tables count a game for both involved teams and must not be summed as independent games.
- Expected calibration error, binned reliability/resolution, outcome uncertainty and the explicit within-bin residual. Proper scores measure both discrimination and calibration, so lower Brier alone does not prove better calibration.
- Last 50 versus preceding 50 log loss. Weekly-block intervals require at least eight represented weeks; smaller/noisy changes remain watch signals. Monitoring is descriptive, repeatedly checked, and affected by schedule difficulty and selection; it does not inherit ADWIN's formal guarantees or authorize promotion.
- Suggested investigations for overconfidence, unusually confident misses, data coverage and changing form. An injury or rest pattern is a hypothesis, not a proven explanation of a loss.

The dashboard shows these in Model lab and the Right / wrong area, alongside source-backed injury reports and current trial progress.

## Actual research evidence

Initial offline studies tested 21 new candidates for each sport plus 21 on modern NBA development: **168 candidate evaluations**, each with chronological folds. This counts specifications tested, not independent hypothesis tests or new games.

WNBA improved on the same 638 development games: **69.2789969% → 69.7492163%** (442 → 445 correct), log loss **.6085960 → .6060434**, Brier **.2096427 → .2088873**. The selected specification is `logistic_context_feedback_w10_C0.03_recent`. Its binned calibration error worsened (.0480 → .0586), so improved proper scores must not be described as proof of improved calibration. This small development-selection gain is optimistic and is not live performance. It qualifies only for a prospective trial; the next WNBA season may be needed to collect results.

The retained specifications won the strict comparison for NBA, NFL, NHL, MLB, UFC and the local CFB cohort. Modern NBA also retained the prior feedback choice; no new 70% claim is justified. The historical NBA confirmation was already reused by prior research and is explicitly not fresh independent evidence. Local CFB runtime history/baseline differs from the deployed runtime; its offline comparison is valid within its own cohort but not directly comparable to deployed metrics. The hourly job recomputes against each deployed baseline. Full source hashes, dates, specifications and metrics are in `artifacts/research/adaptive-error-v1.json`.

## Online references reviewed

- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html): temporal ordering and growing training sets. This project groups by actual calendar dates because sports observations are not equally spaced.
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html): disjoint calibration data, proper scoring rules and the distinction between reliability and discrimination.
- [River ADWIN documentation](https://riverml.xyz/dev/api/drift/ADWIN/): motivation for monitoring changing error distributions. River is not installed and ADWIN is not claimed as implemented; this project uses explicit rolling windows and weekly-block descriptive intervals.

These references guide methodology. They do not demonstrate a betting edge or guarantee accuracy.
