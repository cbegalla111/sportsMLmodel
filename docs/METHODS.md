# Methods, sources and limitations

## Primary sources consulted

- FiveThirtyEight historical NBA dataset and field dictionary: https://github.com/fivethirtyeight/data/tree/master/nba-elo . This is historical game data from Basketball-Reference, distributed under the repository's [CC BY 4.0 license](https://github.com/fivethirtyeight/data/blob/master/LICENSE). We transform it into result-only rows; supplied source Elo/forecasts are excluded. The saved raw-byte SHA-256 and retrieval timestamp identify the exact download.
- FiveThirtyEight's own baseline implementation: https://github.com/fivethirtyeight/nfl-elo-game . Supports transparent rating baselines; we implement our own fixed K=20, home bonus=60 baseline, not a claim of reproducing their full model.
- nflverse documented schedules loader: https://github.com/nflverse/nflreadr/blob/main/R/load_schedules.R . Public results and schedules are maintained at https://github.com/nflverse/nfldata/blob/master/data/games.csv . The project explicitly supplies the dataset for analysis. Keep raw NFL archives private; no blanket redistribution license is asserted here. Attribution: Lee Sharpe and nflverse contributors. Only selected results and schedule fields are consumed.
- scikit-learn primary documentation on chronological validation: https://github.com/scikit-learn/scikit-learn/blob/main/doc/modules/cross_validation.rst . Time-series dependency makes random splitting inappropriate.
- scikit-learn probability calibration: https://github.com/scikit-learn/scikit-learn/blob/main/doc/modules/calibration.rst . Probability quality is evaluated with proper scoring rules and reliability diagrams. No fitted post-hoc calibrator is claimed.

Additional verified primary feeds: MLB official Stats API `/api/v1/schedule` at https://statsapi.mlb.com and NHL official schedule `/v1/schedule/YYYY-MM-DD` at https://api-web.nhle.com . Their raw observed responses, fetch timestamps and hashes are stored privately. No blanket redistribution permission for their raw archives is asserted. MLB uses regular/postseason games only; NHL uses regular/postseason eventual-winner results. Neutral venue is not independently resolved for these feeds; designated home labels may be misleading at special venues. The public NBA CDN was tried at cdn.nba.com but returned HTTP 403.

References were retrieved during implementation. The hosted scikit-learn site was blocked, so its authoritative repository documentation was used instead.

## Fixed computing budget

One CPU, five fixed candidate definitions, three expanding date-block validation folds. First 80% of distinct dates are development data; the last 20% are sealed final test. Development folds train before 40/60/80% of development dates and validate in the next 20% block. Dates are never divided across partitions.

Candidates: transparent Elo; standardized L2 logistic regression C=0.1 with 10- or 20-game rolling histories; logistic with a complete pregame sport-feature group as ablation; histogram gradient boosting (60 rounds, 7 leaves, learning rate 0.05, L2=10). Sport-feature ablation is explicitly skipped when inputs are missing. Preprocessing fits on each training fold only. Lowest mean validation log loss chooses the model. The chosen model and fixed Elo baseline are evaluated once on the final test. Final-test metrics are not used to pick models or parameters. Seed=42 where needed. No random forest, ensemble, recency-weight tuning, broad hyperparameter search, scoring simulations or post-hoc calibration has been validated. Extra complexity requires separate future-only evaluation.

After evaluation, the chosen specification is refit on available history for inference. Those full-data weights are distinct from the development-trained weights used for final-test reporting. Automatic refresh now uses the loss-triggered prospective improvement gate documented below, retaining champion weights until it passes. A second selection run on changed data is deliberately refused. A locked challenger uses a prospectively reserved new evaluation period before changing specifications. Exact held-out forecasts and reports are committed under artifacts; `scripts.export_experiments` verifies reproduction of the existing metrics, without repeating model selection.

## Interpretation

The NBA, NFL, MLB and NHL models are limited result-history baselines. They do not implement possession-adjusted efficiency, EPA, quarterback injuries, opponent-adjusted college statistics, starting-pitcher models, goalie models or fighter-specific models. CFB, WNBA and UFC are data-entry interfaces and schemas until adequate data and validation exist. A generic result baseline is not represented as a validated sport-specific model for those leagues.

Logistic explanations are standardized input contributions to fitted log odds, not causal effects. Other model explanations show inputs without inventing importance values. Advanced inputs that the chosen model does not use are rejected as scenario overrides. Changing neutral venue is supported only if the fitted model has seen neutral-venue variation; otherwise the adjustment is withheld. The home-only historical NBA archive cannot validate that sensitivity. Changing a pitcher/player requires a validated feature model, not a guessed adjustment.

Brier and log loss are primary probability measures; accuracy and AUC are secondary. Reliability bands show sample sizes, mean probability and empirical frequency. Reports group final-test performance by inferred season and calendar year. NBA/NHL seasons are labeled by ending year; NFL/CFB by starting year. Intervals use 200 resamples of calendar-week blocks on fixed test predictions. They approximate performance uncertainty, may understate longer dependence, and do not give game-specific confidence intervals or account for all model-selection uncertainty. No model-disagreement confidence interval is displayed.

Predictions condition on a decisive eventual winner. NFL ties and UFC draws/no contests are excluded, so summing two opponents to one is conditional, not an unconditional three-way outcome. Probabilities are not estimates of settlement under a particular bookmaker's rules. No outcome is certain. No odds comparison is populated without real odds, and no odds affect training.

Models require at least 700 decisive observations over 100 dates. Live forecasts require recent results (at most 30 days old), event date within 14 days, and five prior games per opponent. Date-only features force the forecast date after the latest known result date. Historical test results are not represented as pre-event saved forecasts. Scenarios may use old data but are labeled hypothetical. Injuries, lineups, pitchers, goalies and weather remain unconfirmed. Even fresh NFL output is a limited baseline, not a complete moneyline product.

## Loss-triggered model improvement

Automatic refreshes no longer refit production weights blindly. Each sport retains a champion. Fresh final results update the shifted rating, rest and rolling-history inputs daily; the champion's fitted coefficients remain fixed until a replacement passes the promotion policy.

The public pipeline records the first exported pre-event prediction in a separate public-only ledger. It settles that prediction against final results without replacing earlier probabilities. A settled miss opens a review. Seven fixed logistic/boosted-tree and rolling-window configurations are compared using expanding date folds; archived final-test dates are excluded from validation. The chosen challenger is fitted and locked before its new confirmation window starts.

Both frozen models then predict the same subsequent events, using only earlier dates for input history. At least 100 eligible new results across eight calendar weeks are required. Promotion requires log-loss improvement of at least 0.002, Brier score and accuracy that do not worsen, and an entirely negative 95% paired calendar-week bootstrap interval for the log-loss difference (1,000 samples). Failure consumes that confirmation window; it cannot be reused to tune another challenger. The original held-out benchmarks remain sealed. These gates reduce noisy updates; they cannot guarantee future accuracy.

Initial models for newly supplied sports retain the original three expanding development folds, ten fixed candidates and untouched final 20% of dates. UFC outcomes are encoded as 1/0 winner flags, not physical fight scores; draws/no contests are excluded. UFC has sparse individual histories, so many fights may lack three prior appearances for UFC (five for team sports) and correctly receive no forecast. No current career aggregates are treated as historical pre-fight features.

NBA modern history and schedules are read from https://github.com/sportsdataverse/hoopR-nba-data (nba/schedules/nba_schedule_master.csv), a maintained ESPN-derived mirror. Raw source fields beyond results and fixtures are discarded. Preseason/all-star records and pre-2022 mirror results are excluded, preserving the original 538 benchmark lineage. WNBA and college football use yearly scoreboard requests with an explicit limit of 1,000 and truncation checks; UFC uses monthly requests. Large invalid limits are never treated as complete histories.

Team-history freshness accounts for off-season gaps (180 days for MLB, 240 for NBA/NHL/NFL/WNBA, 300 for CFB). UFC requires three prior appearances within three years and a latest appearance within two years. The overall league result feed must still be fresh, and all forecasts expire at verified starts. First games after long layoffs are result-only baselines with unconfirmed roster changes, not claims of fresh player availability.

College-football final results now use the ESPN-derived SportsDataverse cfbfastR-cfb-data season schedule files, with future fixtures from cfbfastR-data’s public schedule CSV. Teams are joined by source team IDs, not fuzzy name matching. Only result/fixture columns are read; provided ratings and postgame win probabilities are discarded. The source’s current-season results and next-14-day fixtures are verified independently. Exact training event IDs preserve old benchmark/weight lineage when additional historical results are backfilled; they do not authorize changing previously used observations. Additional history updates current shifted inputs but does not silently rewrite weights or old test scores.

## Expanded seven-sport backtest review

Each sport now receives a bounded comparison of 20 challengers plus its incumbent specification on the same three expanding development folds. All validation dates precede the original final-test start; archived final-test outcomes do not influence selection. The shared warm-up cohort makes event counts directly comparable.

The fixed catalog compares 10/20/40-appearance windows, regularized logistic regression, shallow boosted trees, and recency weighting with a sport-specific half-life. A new result-derived feature family adds short form, previous opponents' pre-event strength, performance relative to pre-event expectations, form volatility, recent workload, logarithmic layoffs and experience. All input histories update only after every event on a date has received its features. No injury, lineup, advanced player or bookmaker data is invented.

Candidates cannot be selected with development accuracy or Brier worse than the incumbent, and log loss must improve. Among eligible contenders, the highest winner-picking accuracy determines selection; lower log loss breaks ties. The unconstrained highest-accuracy candidate is also reported separately if it fails the probability-quality checks. The full comparison, exact fold dates, sample sizes and accuracy differences appear in Model Lab. Development improvements after comparing many candidates are optimistic: they are research findings, not a new independent performance guarantee. Existing production champions and already locked trials are preserved. Loss-triggered reviews use this expanded catalog; a replacement still needs the original prospective confirmation gate.

A digest of the development dataset, incumbent specification and research version caches the review. New results continue to refresh input history and settle prior predictions daily without repeatedly re-opening an unchanged development comparison. Candidate weights are fitted afresh when a loss opens an independent trial.

## Probability quality and scoring profiles

The quality review adds chronological temperature/sigmoid calibration and fixed logistic/Elo probability blends. Calibration uses an inner 80/20 **date** split within each outer training fold. The base model sees only the earlier portion; its predictions on the later training portion fit the calibrator. The outer validation period stays untouched by both fits. Base-training, calibration and validation dates are recorded. At least 80 base-training and 30 calibration observations, with both classes in each block, are required; unsupported candidates are explicitly skipped. A final fit that lacks a valid calibration block is marked unavailable rather than silently substituted.

Team sports also compare trailing points scored/allowed, score-normalized margins, margin variability and smoothed venue form. These inputs update only after all events on a date. Fight winner flags are never treated as physical scoring data; UFC excludes this feature family. The bounded catalog now has 67 team-sport and 54 UFC challengers, including the previous candidates.

Out-of-fold diagnostics now include balanced accuracy, precision/recall for the home or first opponent, and fixed-bin calibration error alongside log loss, Brier and accuracy. A paired calendar-week bootstrap estimates development accuracy/log-loss differences. Those intervals do not account for candidate-selection optimism and are not independent evidence for promotion. Existing production gates and locked trials stay intact. Calibrated/blended models expose raw inputs without invented linear contribution scores.

For sparse fighter histories, the common first validation date can move later until the *preceding training data* meet the inner calibration sample/class requirements. Three expanding folds then share the remaining development dates across every contender, including the incumbent. This readiness decision uses no validation scores. Such a changed cohort is not directly comparable with earlier review percentages; the paired incumbent/challenger comparison on the new cohort is the relevant comparison.

## Accuracy-focused rating and nonlinear review

The expanded catalog adds slow/fast Elo ratings, season-regressed strength, exponentially weighted form and (for team sports only) margin-weighted ratings and normalized margins. All features are calculated before any outcomes on the event date update history. UFC additions use outcomes and layoffs, not physical interpretations of fight score encodings.

Additional estimators are regularized extra trees (120 trees, bounded depths, minimum leaf size 20), a reproducible 64-component RBF kernel approximation with regularized logistic regression, and an equal-weight logistic/boosted-tree/extra-tree ensemble. These are small fixed searches, not an exhaustive claim of the highest possible future accuracy. Shorter recency half-lives are also compared.

Decision-boundary calibration tests 33 log-odds offsets only in the inner chronological calibration block. Its accuracy-maximizing offset must also preserve or improve that block's log loss and Brier. The outer validation folds never tune a calibrator or ensemble weight. Winner labels consistently use the opponent with probability at least 50%.

Model Lab sorts all candidates by development accuracy and shows the highest-accuracy candidate separately when the eligible selection differs. Final historical tests remain sealed. First published live picks stay immutable, and an expanded search does not reset a locked challenger or bypass prospective promotion.

## Sport-specific recovery and outcome feedback

`prediction_policy=sport-rest-v1` corrects recovery inputs in current forecasts while retaining champion weights. Days since an event are not medical recovery. The policy uses the following fixed schedule heuristics, chosen before the comparison rather than tuned to the Philadelphia–Cleveland outcome:

| Sport | Typical spacing (days) | Recovery credit cap (days) | Long-inactivity threshold (days) |
|---|---:|---:|---:|
| NBA | 2 | 3 | 21 |
| WNBA | 2 | 4 | 28 |
| NHL | 2 | 4 | 28 |
| NFL | 7 | 10 | 35 |
| CFB | 7 | 10 | 42 |
| MLB | 1 | 3 | 14 |
| UFC | 90 | 180 | 730 |

Recovery differences saturate at the cap. If either opponent lacks prior observations or exceeds the inactivity threshold, the recovery comparison is neutralized; the code does not infer extra fitness, an injury or an actual recovery period. UFC differences use 90-day units rather than hundreds of raw days. Legacy form-model layoff inputs use the same bounded, sport-normalized comparison. New contextual feature models learn a separate long-inactivity indicator and missing-history flag, rather than equating inactivity with a benefit.

Model Lab isolates the input correction by fitting the old specification with original inputs and comparing the same coefficients on old versus corrected validation inputs. That historical reference is diagnostic only and cannot win selection. All eligible candidates and prospective confirmation scoring use the same inference policy as the public forecast. Additional contextual models are trained directly on the corrected recovery inputs, alongside a no-rest ablation. The catalog adds 11 challengers (78 team-sport / 65 UFC), plus an original-rest diagnostic reference where applicable. The archive's original held-out tests remain unchanged.

Public first-published picks are immutable and new records retain the policy version. Actual imported outcomes settle those original picks; misses trigger supervised challenger review. Promotion still requires independent improvements in log loss, Brier and accuracy. A policy correction never rewrites old wins/losses. If a confirmation trial was opened under an older input policy, its weights remain locked and its confirmation start moves forward so evidence from different policies is not mixed.

Feedback is tracked separately for each prediction policy. The first global published pick remains immutable, and each policy also keeps its first pre-game pick for that event. Both versions appear in history with policy labels and separate accuracy summaries. Current-policy losses trigger current-model reviews; old-policy losses and pending counts are not mixed into that record. Switching feedback policy starts its consumed-loss counter at zero, so prior counts cannot prevent a new missed pick from being reviewed.

## Bayesian strength, stacking and shorter training histories

The v7 catalog adds 32 fixed challengers (110 team-sport / 97 UFC total). Glicko-style latent strength features maintain separate rating means and uncertainty, let uncertainty increase with elapsed calendar time, and update all opponents only after every event on a date has received features. These are result-derived modeling assumptions, not measured player health or game-specific probability intervals. The contextual variant preserves the sport-specific rest policy.

Additional classifiers include bounded 160-tree random forests and standardized 16-unit neural networks with two fixed regularization levels. Neural-network early stopping on a random validation split is disabled; all model selection remains chronological. Temporal stacking fits logistic, shallow boosting and extra-tree base models on the earlier 80% of training dates, then fits a regularized logistic combiner on the later 20%. Outer validation games train neither base models nor the combiner.

Training-history ablations use only the latest fixed number of years within each training fold: 4/8 for NFL and CFB, 1/3 for MLB, 3/6 for UFC, and 2/4 for NBA/WNBA/NHL. Feature histories remain causal and can use earlier known results. A horizon with fewer than 100 training observations or a missing class is skipped rather than compared on easier validation games.

The previous research winner is compared with the new selection only when development hashes, validation dates and validation sample sizes match exactly. All old challengers remain in the search, no final-test outcome is used for selection, and lower log loss/non-worse Brier are still required. Searching more candidates can overfit development folds; the existing prospective confirmation gate remains mandatory for replacing champion weights.

## Score-target models and direct Bayesian priors

The final expanded catalog contains 130 team-sport and 101 UFC challengers. It includes a direct probability from the pre-event uncertainty-adjusted strength log odds, with optional inner-block temperature, sigmoid or decision calibration.

For team sports only, Gaussian margin models learn final home-minus-away scoring margins with regularized ridge regression. Poisson models separately learn home and away final scoring counts, then use a Skellam difference distribution to estimate the winner, splitting unresolved ties equally. These auxiliary models do not claim regulation-only, draw-market or bookmaker-settlement probabilities. Fixed regularization settings are compared with and without inner chronological sigmoid calibration.

Physical scores are passed separately as **training targets**, never appended to predictor columns. An outer validation game's score cannot enter either base fitting or calibration. UFC winner encodings are explicitly rejected as physical scoring targets. Query-time inference uses only causal result-history features, including the existing sport-specific recovery policy.

The one-time public build timeout is 45 minutes to accommodate the expanded CPU-only comparison. Subsequent daily runs reuse unchanged development research; new public results still update inputs and policy-specific outcome feedback. A larger candidate search does not bypass sealed tests or prospective model promotion.

## Targeted UFC, MLB, NHL and NFL review (v9)

This fixed expansion adds 20 candidates to each requested sport. UFC form windows are 3, 5 and 8 prior fights; NFL windows are 5, 8 and 16 games; MLB windows are 5, 15 and 60 games; NHL windows are 5, 15 and 30 games. Contextual form and uncertainty-adjusted rating inputs are tested with two regularization strengths. These windows do not change the shared minimum-history cohort or chronological validation dates.

Eight additional nonlinear candidates per sport use temperature or sigmoid calibration with neural networks or random forests. Calibration is learned from predictions on the final 20% of outer-training dates, generated by a predictor fitted only on the earlier 80%. After freezing that calibration, the predictor is refitted on all outer-training rows. The audit separately records the calibration predictor's training boundary and the final refit boundary. Every outer validation game remains unseen throughout fitting and calibration. Calibration transfer after refitting is a hypothesis tested by the outer folds, not an assumed improvement.

All previous candidates remain available. Selection still requires non-worse winner accuracy and Brier score plus lower log loss than the incumbent. Newly selected research weights remain separate from production until the existing prospective loss-review promotion checks pass. Neither searching more candidates nor a development backtest establishes future accuracy.

## NBA outcome feedback (v10–v11)

The NBA review adds 23 candidates while leaving other sports' research catalogs and caches unchanged. New contextual feedback inputs track online margin strength, short-term unexpected wins, unexpected margins, short-versus-long residual momentum, squared prediction errors, and prediction loss. The internal causal predictor estimates home margin from team strengths plus three home-court points and maps margin to probability with a fixed 12-point logistic scale. Its outcome residual is `y - p`: confident mistakes cause larger corrections than expected wins. Wins and losses both contribute. Margin updates clip residuals at 30 points, and seasonal strength shrinks toward neutral to limit blowouts and old-season carryover. These are hypotheses, not claims of optimal NBA constants; fixed logistic, kernel and tree candidates test the signals. Temperature/sigmoid calibration is fitted chronologically before an outer-training refit. After the first 20 candidates showed better probability loss but slightly lower winner accuracy, one follow-up tested three fixed blends (25%, 50%, 75% feedback weight) with the previous contextual form specification. Their weights are fixed before fold scoring, rather than fitted on validation games; this remains development research with selection optimism.

All features for a date are emitted before any outcomes from that date update state. Same-date feedback is batched; hypothetical queries never update state. Internal residuals are not substituted for the immutable live saved-pick record. The latter separately supplies actual accuracy, Brier/log loss, confidence bands, and the largest confidently missed picks.

A later-era diagnostic refits the previous and newly selected research specifications before each of the last three completed July-to-June seasons, then scores the following season. Those specifications are fixed by the older development search before this audit. Audit scores do not select models, overwrite the original sealed test, or authorize promotion. A separate NBA candidate is locked after actual forecast losses alongside the existing trial; it cannot be swapped mid-trial. Both candidates require the same independent 100-result, eight-calendar-week, accuracy/Brier/log-loss/bootstrap gates. A changed champion invalidates the additional candidate's reference comparison.

Online sources checked for this work:

- [scikit-learn: stochastic gradient descent](https://scikit-learn.org/stable/modules/sgd.html), explaining logistic log-loss learning and its tuning limitations. This informed residual-based updates; no claim that an SGD solver alone increases accuracy.
- [NBA statistics glossary](https://www.nba.com/stats/help/glossary), defining possession-adjusted offensive efficiency and effective field-goal percentage. The result-only signals here are **not** labelled as these advanced statistics.
- [hoopR public NBA schedule/results mirror](https://github.com/sportsdataverse/hoopR-nba-data/tree/main/nba/schedules), the verified current result and fixture feed. Its team-box-score schema was inspected for future efficiency research; box-score fields, injuries and player availability are **not** fitted features in this change. No live or historical sportsbook probabilities enter the model.

### NBA recent-data selection and historical confirmation

A separate recent-data study uses the same fixed 153-candidate catalog. It selects only on results from January 2022 through June 2025, using three expanding date folds. July 2025 through June 2026 supplies a separate historical confirmation period; current-season games do not participate in selection or confirmation. The original 2013–2015 sealed test is absent from this research dataset. This follow-up was designed after inspecting the older specification's three-season audit; the confirmation is historical evidence and does not establish an untouched prospective experiment. Its scores are not used to tune candidate weights or thresholds, and no further search is performed against that period.

The prior and selected specifications receive the same recent training history and confirmation cohort. A passing recent candidate must have non-worse winner accuracy and Brier and lower log loss. The artifact records `history_from=2022-01-01`; both live and trial inference honor that history boundary rather than reconstructing a different feature state from older results. Recent research and its candidate are cached separately. After a real forecast loss, a passing recent candidate takes priority for the additional locked NBA trial. Current-season outcomes may fit future weights, but never retrospectively improve the reported confirmation score. Independent prospective promotion requirements remain unchanged.

Following subsequent misses, the primary loss-review path refits this frozen recent specification on the latest results without changing its selected hyperparameters. The additional trial does the same at lock time if an older candidate is already being evaluated. Refit weights and their training-event lineage are separate from cached research weights; an ongoing trial is never refreshed with the outcomes on which it is being graded. Identical primary/additional candidates are not duplicated.
