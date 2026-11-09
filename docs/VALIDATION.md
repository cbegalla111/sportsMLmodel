# Verified implementation evidence

Validation performed October 20, 2026 in the cloud workspace; reports describe observed runs, not a hosted deployment.

- Clean Python 3.12 virtual environment installation from requirements.txt succeeded. `pip check` reported no broken requirements. The reusable install script also ran successfully on the current instance.
- `python -m pytest -q`: **22 passed** in the final suite (21 before adding the MLB preseason regression). Covers atomic/idempotent ingestion and restart persistence, conflicting IDs, invalid dates/scores/outcomes/market fields, timestamped features, ties/no contests, same-day/current-result leakage, expanding fold chronology, sealed final-test reuse, frozen-model refitting, probability sums, insufficient-data and stale-data withholding, scenario input validation, authenticated/anonymous access, CSRF, cross-origin rejection, logout, brute-force rate limiting, and feed failure behavior. Test fixtures are synthetic and are not loaded into the live database.
- NBA: 14,208 genuine home-game results, November 2, 2004–June 16, 2015. Fixed candidate selection chose logistic with a 20-game window. Final test April 28, 2013–June 16, 2015: n=2,676, log loss 0.60827246, Brier 0.21058384, accuracy 0.66218236, AUC 0.71801108. Elo baseline Brier 0.21298619. Brier approximate 95% week-block interval [0.20379485, 0.21821061]. No claim of current NBA forecasts.
- NFL: 5,791 genuine stored results, including 15 ties; 5,776 decisive games through October 19, 2026. Selected logistic with a 10-game window. Final test December 4, 2022–October 19, 2026: n=1,048, log loss 0.63577201, Brier 0.22274950, accuracy 0.64408397, AUC 0.68598984. Elo baseline Brier 0.23000961. Approximate Brier interval [0.21565787, 0.23249236]. Predictions condition on no tie. Current inputs are results only, with injuries/QBs/weather unconfirmed.
- For each league: four candidate specifications completed; the fifth, advanced sport-feature ablation, was skipped because complete pregame features were unavailable. Unsuccessful candidates are retained in the reports. These are not exhaustive feature/hyperparameter searches.
- Already-selected development-trained test forecasts were reproduced exactly (Brier/log loss tolerance 1e-12), then exported with season summaries and full-history inference weights to artifacts/. No model selection was repeated for this export.
- HTTP checks: anonymous state 401; incorrect login 401; correct login 200; authenticated state 200; missing CSRF 403; foreign Origin 403; saved settings 200; stale NBA live forecast 400; hypothetical NBA forecast 200 with complementary probabilities. Limited NFL inference also returned complementary probabilities. These smoke entries are labeled in the persistent ledger.
- Chromium desktop: signed in, selected NBA matchup, generated a hypothetical prediction, rendered ten calibration bands, switched to empty CFB and saw 0 events / Not validated. No JavaScript page errors. Mobile 390px viewport had 390px body width after responsive layout correction. NFL had 28 source-backed upcoming fixture options at validation time.
- Stopped and restarted both web server and updater. Reauthenticated and verified identical saved prediction IDs and selected-league setting; the worker restarted, logged feed checks, and preserved the daily backup marker.
- Created a SQLite-consistent backup, restored it to a new directory, verified every archived checksum and SQLite integrity, and recovered 19,999 events plus the three saved ledger records present at backup time. Authentication was intentionally excluded.
- Automatic NFL refresh succeeded. MLB Stats API, current NBA CDN and NHL API received proxy 403 network-policy denials. Source adapters for those endpoints are implemented but not live-validated. WNBA/CFB/UFC remain honest CSV/manual fallbacks. After the saved network additions took effect, MLB and NHL became reachable and were collected/validated as described below. No full private website deployment or public publication occurred.

A fresh separate runtime seed succeeded: archived NBA/NFL data digests verified, both initial model artifacts restored, backup created, and the then-current 21-test suite passed. Once network additions became effective, that seed also imported the recent NHL schedule. The final repeat installation preserved all four league datasets and passed all 22 tests. The initial Docker build encountered container DNS restrictions; an offline wheel cache downloaded over verified TLS provided a successful build path. The non-root Docker image passed the same 21 tests without network, and its running loopback-only service passed homepage, anonymous denial and authenticated seven-league-state readiness checks. Initial Docker source permissions were corrected with explicit non-root ownership before those successful checks. Tests run against local ephemeral HTTP servers; no live sports results are invented by tests. The GitHub Actions workflow is included but no remote CI result is claimed without observing it.

## Additional verified feeds and experiments

- MLB: 7,413 regular/postseason finals, March 20, 2024–October 19, 2026. An initial response included preseason ties; the corrected adapter excludes preseason/all-star events, preserves valid games, and has a regression test. Three expanding folds selected logistic with a 20-game history. Final test June 10–October 19, 2026: n=1,462, log loss 0.68569111, Brier 0.24628031, accuracy 0.55608755, AUC 0.55737334. Elo Brier 0.25124652. This is weak signal; no starting-pitcher/lineup advantage is claimed.
- NHL: 2,932 genuine regular/postseason games from weekly official API snapshots, October 4, 2024–October 19, 2026. Selected logistic, 20 games. Final test March 20–October 19, 2026: n=441, log loss 0.67066805, Brier 0.23889326, accuracy 0.60090703, AUC 0.62600702. Elo Brier 0.24131447. Starting goalies and expected goals remain unavailable.
- Total normalized stored results: 30,344 across four leagues (including 15 NFL ties). All four benchmark reports, selected inference weights, exact held-out forecasts and season summaries are saved in artifacts/. Current NBA CDN still returned HTTP 403 on alternate public schedule paths; no unverified schedule was substituted.
- Final timestamp validation normalizes timezone offsets before the pre-event cutoff, preventing a nominal previous-day timestamp from leaking next-day UTC information. Neutral-site scenarios are withheld when a fitted model has no neutral-site training variation.

Final four-league backup restoration verified 30,344 stored results, all three saved prediction records, every archived checksum, and SQLite integrity. The final offline Docker image passed all 22 tests.

## Private development preview — October 21, 2026

- Added portable checkout/runtime paths, a GitHub Codespaces devcontainer and private port startup, VS Code tasks, and authenticated development-only automatic page refresh. The configuration validates against the official devcontainers draft-2019-09 JSON schema.
- Final suite: 24 tests passed, including HTTPS-proxy Origin/CSRF checks, Secure cookies, ignored spoofed forwarded-host headers, and authenticated opt-in live refresh. Production framing restrictions and login requirements remain enabled.
- Browser check: signed into the real local dashboard, changed and restored a temporary stylesheet comment, observed automatic navigation and authenticated state after each reload, and verified desktop/mobile rendering with no JavaScript page errors. The browser test was adjusted to observe navigation directly because the app's existing CSP correctly rejects string eval; CSP was not relaxed.
- Repeated preview start reused the existing service. Managed restart succeeded and retained the existing prediction ledger/settings. A relocated checkout path with explicit runtime/venv overrides was verified. The current live service is private and local; no Codespaces instance has been provisioned or remote forwarded URL verified from this task. The user must open/create the linked Codespaces workspace for the configured remote preview.

## Public Pages dashboard and daily pipeline — October 21, 2026

The user explicitly approved a public GitHub Pages dashboard and requested daily data/model updates. Added a real root index, public-only snapshot exporter, detailed seven-sport Forecasts/Model Lab/Data & Sources views, and a daily 11:17 UTC GitHub Actions deployment workflow. The original private app remains separate.

- Final local suite: **31 passed**. Added tests for strict public-source filtering, private history/credential exclusion, untouched ledgers, archived-data lineage checks, stale feed withholding, duplicate fixtures, probability consistency, same-day verified start times, past-event withholding, daylight-saving conversion of NFL kickoff times, and rejection of stray files in public publish directories.
- Browser checks under the actual `/sportsMLmodel/` base path passed: seven sport tabs, ranked forecast selection, model metrics/calibration views, data/team tables, empty/unvalidated sports, historical-only NBA, 390px mobile layout, and overdue-snapshot probability withholding. No JavaScript, HTTP-resource or CSP errors remained.
- Public snapshot generated from actual allowlisted results and committed public model artifacts: 28 NFL, 95 NHL and 7 MLB limited pre-event forecasts at build time. Counts change with sources and event start/expiry; they are not guarantees. NBA/CFB/WNBA/UFC had no current forecasts and were labeled accordingly.
- The exporter refit the frozen specifications in an isolated temporary database. It did not publish private uploads, private model weights, authentication files, personal settings or prediction history. Public estimates did not write the original ledger.
- Date-grouping optimization was compared against the previous feature builder for every current decisive row in NBA (14,208), NFL (5,776), MLB (7,413), NHL (2,943); all feature values matched exactly. Historical model selection/test metrics were not repeated or retuned.
- Daily training uses the selected specification; source data and training hashes/timestamps are shown separately from sealed archived test scores. Fresh verified event-start timestamps permit eligible same-day forecasts; date-only uncertain starts are withheld conservatively.

Remote deployment and scheduled run status are verified separately after pushing the workflow. A local build by itself is not evidence of successful GitHub publication or future scheduled runs.

### Verified GitHub publication

Commit 0694683 was pushed to main. Remote Verify lab CI succeeded. The first [Daily model dashboard build and deployment](https://github.com/cbegalla111/sportsMLmodel/actions/runs/39640719167) completed successfully, including fresh public-source ingestion, daily refits, cache save, Pages artifact upload and deployment. HTTPS requests to the exact public site returned the real root dashboard and a newer runtime-generated model snapshot (October 21, 2026, 17:07 UTC) containing 28 NFL, 95 NHL and 7 MLB forecasts at that time. No future scheduled execution is claimed: the daily cron is configured and the same pipeline's push-triggered run was actually verified.

The app integration lacks administrative permission to change the Pages source setting, but that did not prevent a successful custom Pages deployment under the existing main/root configuration. The workflow now runs for every main-branch push as well as daily, preventing a documentation-only legacy deployment from remaining the final stale snapshot after a successful refresh. The backend updater was restarted with its new daily default and authenticated readiness/persisted history were verified.

The cloud Chromium trust store does not include this environment's outbound proxy CA. Direct browser navigation hit a sandbox certificate error; TLS verification was not disabled. Public HTML/JSON were verified using Python's default trusted TLS configuration, and live resources were rendered through a same-origin TLS-verified fetch bridge for the browser check.


## October 21: seven feeds, guarded champions and compact dashboard

- Local suite: **38 passed**. Additional checks cover outcome-only ESPN parsing, UFC winner flags and neutral status, insufficient/failed promotion evidence, paired weekly improvement testing, immutable first exported forecasts, loss-triggered challenger locking, exact training lineage during historical backfill, rejection of revisions to trained observations, and equivalence of batch pregame inputs.
- [Verified seven-sport deployment](https://github.com/cbegalla111/sportsMLmodel/actions/runs/39654966477): all seven source checks succeeded. Its public snapshot was fetched over verified HTTPS at 18:41 UTC. Coverage: NBA 20,306; NFL 5,791 including ties; NHL 2,943; CFB 4,387; WNBA 1,429; MLB 7,413; UFC 2,776 including draws/no contests. Snapshot forecasts: NBA 99, NFL 28, NHL 95, CFB 114, WNBA 5, MLB 7, UFC 17. Counts are time-dependent.
- NBA now uses the complete modern SportsDataverse schedule mirror. CFB uses complete ESPN-derived season result files plus source-ID-joined upcoming fixtures. Direct current-season scoreboard requests were found to return only 25 CFB events; they are no longer used as its result or schedule source. The historical benchmark remains the exact originally evaluated subset; adding previously absent history does not relabel it as a current full-data evaluation.
- New sport archived baselines are real chronological evaluations, not claimed upgrades of old champions. WNBA: n=317, accuracy 0.706625, log loss 0.588351, Brier 0.200639. UFC: n=284, accuracy 0.602113, log loss 0.675852, Brier 0.241403. CFB’s original partial-history benchmark is weak (n=95, accuracy 0.536842, log loss 0.825707, Brier 0.287241); its weights remain subject to the same prospective improvement gate. No artificial accuracy gain or approved challenger promotion is claimed.
- Desktop and 390px mobile Chromium checks visited all seven sports and all three sections using actual public outputs. No JavaScript errors or horizontal overflow; team search worked and cleared on sport switches. Removed oversized hero headings and long warning blocks; source/model details remain in compact status and expandable sections. Screenshots were kept outside the repository.
- Forecast weights are no longer blindly refitted. Daily checks refresh inputs and settle saved picks. A miss can open a review; promotion requires at least 100 subsequent eligible results in eight calendar weeks, log-loss gain ≥0.002, non-worse Brier/accuracy and a negative paired weekly bootstrap interval. Cached champions are not rewritten by historical input backfills.

## Expanded model review

All seven sports completed 20 challenger comparisons, each using three expanding development folds that exclude the original final-test dates. The results are in [MODEL_REVIEW.md](MODEL_REVIEW.md) and the public Model Lab. These development gains are candidate-selection results; production weights were not promoted on that evidence alone. The daily independent loss-review gate remains active.

The suite now has **45 passing tests**, including same-day leakage checks for the richer feature family, shared fold/cohort checks, original final-test mutation invariance, direct/batched challenger forecast equivalence, and reuse of a promoted model’s actual specification in later reviews. No synthetic results enter production. The two introductory header lines were removed while the Courtside brand, date and refresh control were retained.

Feedback settlement also excludes ties/no contests from wins and losses, settles them rather than leaving them pending, and resolves doubleheaders by event ID. Distinct same-day fixtures retain separate forecasts. Regression tests cover all three cases so incorrect settlement cannot drive a loss-triggered model change.


## October 22: probability quality review

- **50 tests passed** locally. Coverage includes temporal calibration boundaries, shared readiness-based folds, exclusion of sealed final-test outcomes, one-class/small calibration rejection, calibration/blend serialization, normalized scoring-profile leakage checks, exclusion of physical score profiles for UFC, direct/batched profile inference, and accurate Elo input attribution.
- The complete [quality deployment](https://github.com/cbegalla111/sportsMLmodel/actions/runs/39803920543) evaluated 40 candidates for each of six team sports and 32 for UFC. All completed on common per-sport folds; all seven feeds were fresh in the verified public snapshot. Team-sport selections did not change. UFC identified temperature-calibrated Elo with reduced development log loss/Brier/calibration error and unchanged accuracy. See MODEL_REVIEW.md for actual values and cohort limitations.
- Calibrators use only an inner, later training block; outer validation and the archived final test are not used in calibration fitting. Insufficient final calibration data produce an unavailable candidate and a retryable loss review. They do not silently substitute an uncalibrated model or change production weights.
- Development bootstrap intervals explicitly exclude selection uncertainty and are not promotion evidence. Existing locked trials remain unchanged. Production weights were not promoted by this development review.

## Expanded accuracy review (October 22, 2026)

Verified published GitHub Pages research results for all seven sports are recorded in `artifacts/research/accuracy-review-v5.json`. These are paired development comparisons on the same three chronological folds within each sport, with archived final-test dates excluded. Initial validation cohorts can differ between environments; the following are the public deployment's matched comparisons, replacing preliminary local results. The selection prioritizes winner accuracy while requiring lower log loss and non-worse Brier.

| Sport | Incumbent accuracy | Eligible selection accuracy | Highest candidate accuracy |
|---|---:|---:|---:|
| NBA | 68.50% | 69.24% | 69.24% |
| NFL | 63.79% | 65.11% | 65.11% |
| NHL | 54.31% | 55.36% | 55.85% |
| CFB | 73.19% | 73.53% | 73.53% |
| WNBA | 68.34% | 69.44% | 69.44% |
| MLB | 55.52% | 55.86% | 56.32% |
| UFC | 60.56% | 60.56% | 60.56% |

All 67 team-sport challengers and 54 UFC challengers completed. The highest candidate can fail the probability-quality checks; it is reported separately rather than automatically promoted. Comparing many candidates introduces selection optimism. These percentages are not new independent test scores or evidence of a live-model promotion. UFC's selected temperature-calibrated Elo improves probability loss over the incumbent without an accuracy gain.

Validation: 65 automated tests passed, including same-date leakage checks for both team and combat rating features, archived-test outcome mutation, common temporal folds, nested calibration, frozen estimator serialization, direct/batch inference for linear/kernel/ensemble models, and loss-triggered promotion checks. Desktop/mobile Model Lab rendering was checked with actual exported reports. The GitHub build and deployment succeeded, all seven published review versions and completed candidate counts were verified, and live HTML/JavaScript matched the committed assets.

## Contextual recovery correction

The `sport-rest-v1` input correction and outcome-trained contextual challengers are documented in METHODS.md. `artifacts/research/contextual-rest-v1.json` records verified published seven-sport chronological development evidence, including original versus corrected rest with the same fitted coefficients. No final-test outcome is used to choose recovery parameters. The input correction is a declared policy change, not a claim that all accuracy or probability metrics improve. New model weights still require independent confirmation.

86 automated tests pass, including policy-specific outcome feedback without rewriting original picks, sport-specific saturation, offseason/missing-history neutrality, same-date leakage protection, raw-weight identity in the correction backtest, live/confirmation inference parity, contextual-model direct/batch parity, and restarting evidence under a new policy without changing locked model weights. Desktop/mobile checks verify the actual Philadelphia–Cleveland matchup reports its 2-day versus 149-day recorded gaps while assigning zero recovery advantage, shows the sport-specific policy, and exposes the backtest comparison. Original published picks are not rewritten.

The seven-sport deployment completed successfully. All 78 team-sport / 65 UFC challengers completed, all seven published feedback records identify `sport-rest-v1`, and live HTML/JavaScript matched the committed assets. The public Philadelphia–Cleveland forecast had zero recovery difference, with source-history gaps of 2 versus 149 days. The checked-in public snapshot was refreshed too, so the branch-based Pages build does not temporarily restore the previous rest policy.

## Expanded v7 search

The v7 catalog contains 110 team-sport and 97 UFC challengers. It adds causal uncertainty-aware strength features, nested temporal stacking, regularized neural networks, random forests and fixed recent-history training windows. No archived final-test date is used for candidate selection. New versus previous search metrics are shown only for exactly matched development games.

96 automated tests passed, including Bayesian same-date outcome isolation and query independence, nested stacking audit boundaries, recent-horizon exclusion of old labels, frozen model serialization, direct/batch contextual inference, policy-specific actual-result feedback, and rejection of unmatched previous-search comparisons. Real public-source backtests are run by the public dashboard deployment; gains are reported only where measured, and existing promotion checks remain in force.

## Final expanded score-model search

The final catalog includes 130 team-sport / 101 UFC challengers, adding separately supplied score targets for ridge margin and Poisson count models, alongside direct uncertainty-adjusted strength priors. 114 automated tests passed. Additional tests prove that inner calibration-block score targets cannot affect a scoring model, verify scoring-model serialization and direct/batch inference, and reject interpreting UFC winner flags as physical scores.

The highest raw accuracy candidate and the eligible selection are distinct. A higher winner percentage is not reported as an overall improvement when its probability loss/Brier worsen. Previous-search comparisons require identical development game hashes, fold dates and sample sizes. All original test dates remain excluded from candidate selection.

## Verified final results for the expanded accuracy request

`artifacts/research/accuracy-search-v8.json` records all seven published results. Each start-of-request comparison has an identical development hash and the same validation dates/sample sizes. The table compares the eligible research winner at the beginning of this request with the final selection, and separately lists the highest raw accuracy found.

| Sport | Prior eligible winner | Final eligible winner | Highest raw accuracy |
|---|---:|---:|---:|
| NBA | 69.01% | 69.01% | 69.30% |
| NFL | 64.88% | 64.88% | 64.92% |
| NHL | 55.57% | 55.57% | 56.13% |
| CFB | 73.64% | 74.21% | 74.21% |
| WNBA | 69.28% | 69.28% | 69.28% |
| MLB | 55.81% | 55.81% | 56.27% |
| UFC | 60.56% | 60.56% | 60.80% |

College football improved its eligible winner accuracy; the other six eligible winners did not improve accuracy over their prior research winner. NBA reached a higher raw accuracy candidate but worsened probability loss/Brier; it was not treated as an overall improvement. These results do not substantiate higher winner accuracy in every sport. Original sealed test metrics and independent prospective promotion checks remain unchanged.

The public workflow, all 130 team-sport/101 UFC challengers, and 114 tests completed successfully. Desktop/mobile Model Lab checks verified the complete candidate catalog, matched prior-search comparison, raw accuracy leader and no viewport overflow. Live HTML/JavaScript matched committed assets. The checked-in public snapshot was refreshed from the verified deployment.

## Targeted four-sport review (v9)

The deployed review completed 150/150 challengers each for NFL, NHL and MLB, and 121/121 for UFC. The additional 20 candidates per sport test sport-specific history windows and chronologically calibrated/refitted nonlinear estimators. All 115 automated tests passed, including calibration freezing and serialization checks. `artifacts/research/targeted-four-sport-v9.json` preserves the measured comparison against the previous public v8 review; development hashes, validation dates and sample counts were verified identical.

| Sport | Prior winner accuracy | New winner accuracy | Prior log loss | New log loss |
|---|---:|---:|---:|---:|
| UFC | 60.56% | 60.56% | 0.676187 | 0.676187 |
| MLB | 55.81% | 55.81% | 0.682827 | 0.682827 |
| NHL | 55.57% | 55.57% | 0.687520 | 0.687033 |
| NFL | 64.88% | 64.88% | 0.630148 | 0.630148 |

NHL selected contextual logistic form with a five-game window and C=0.03. On the same 1,427 development games, its Brier score also decreased from 0.247191 to 0.246871. The improvement is in probability scoring; winner accuracy did not rise. The other three sports retained their prior eligible selections. These results do not establish an independent or future gain; research candidates still require prospective promotion before replacing live weights. Daily updates include the expanded search, with unchanged development reviews cached.

## NBA outcome-feedback and recent-data review

The NBA-specific catalog adds 23 candidates (153 total), including causal win/margin error features, calibration and three fixed probability blends. The older development winner remains at 69.01%; lower-loss feedback/blend candidates did not improve that winner percentage. Original final-test metrics remain unchanged.

A separate study selects from the same catalog on January 2022–June 2025 results, then confirms the fixed selection on July 2025–June 2026. `artifacts/research/nba-outcome-feedback.json` records the complete recent review and comparison cohort hash. Both specifications use identical recent training history and the same 1,322 confirmation games:

| Specification | Winner accuracy | Log loss | Brier |
|---|---:|---:|---:|
| Previous contextual form | 68.23% | 0.607856 | 0.209461 |
| New contextual NBA feedback | 68.38% | 0.603939 | 0.207853 |

The gain is **two additional correct winners**, not evidence of a large or guaranteed future advantage. This recent study follows an older-specification three-season audit; it is historical confirmation, not a wholly untouched prospective experiment. Selection, training-history boundaries, cached research and immutable live trials remain separate. Current-season results are excluded from selection/confirmation but may fit future candidate weights. Passing historical checks gives priority for a locked NBA candidate; production weights still require the existing independent 100-result/eight-calendar-week gate.

The live saved-pick record at the start was 6 correct and 8 missed under the current prediction policy. The UI now shows this actual record, descriptive uncertainty, confidence bands and confidently missed picks separately from backtest percentages. Testing covers date/future isolation, same-date feedback batching, frozen calibration/blends, exact live/batch feature inputs, recent-history inference boundaries, fresh-data refits without hyperparameter reselection, immutable parallel candidates and guarded promotion.

All 137 automated tests passed locally. Desktop (1440px) and mobile (390px) checks verified the actual saved-pick record, all 153 recent candidates, both confirmation percentages, and no viewport overflow or JavaScript errors.

The GitHub workflow also passed and the public deployment was verified. All 153 older-period and recent-data NBA candidates completed. The recent candidate was locked after October 24 results with zero confirmation games at publication; the older trial and champion remained intact. All 14 previously settled current-policy picks were verified unchanged, and deployed HTML/JavaScript/CSS matched the source. The committed snapshot was refreshed from the verified public deployment.

## NBA 70% target follow-up

The source check matched **6,114** validated public box-score games to imported final results. All **18** additional candidates completed. The development-selected 50/50 box-score/feedback blend was tested on the same **1,322** historical confirmation games as the existing candidate:

| Model | Correct winner accuracy | Log loss | Brier |
|---|---:|---:|---:|
| Retained NBA feedback candidate | 68.38% | 0.603939 | 0.207853 |
| New box-score blend | 67.85% | 0.603645 | 0.207772 |

The new model reduced probability errors slightly but made seven fewer correct winner picks. It failed confirmation acceptance and was not adopted. The supported target reference remains 904/1,322 correct (68.38%). Achieving at least 70% on this cohort would require 926 correct: **22 additional correct picks**. The study did not verify 70% accuracy. No hard games were removed, no current-season outcomes tuned these candidates, and the original archived test and locked live trials remain intact. The confirmation period is reused historical evidence, so none of these results is labelled a fresh independent test.

The optional source updater preserves cached observations on failure. Tests cover source identity and UTC dates, score arithmetic, earlier-date isolation, missing-data cohort retention, blend input parity/serialization, an explicit isolated research catalog, historical caching despite new current-season data, and displaying the retained model's target score after a failed experiment.

All **146 tests passed** locally and the GitHub deployment completed successfully. Desktop/mobile checks verified the retained score, failed experiment, 70% target, 22-pick gap, complete 18-model catalog and no overflow or JavaScript errors. The live source matched 6,114 games. Both locked trials, production champion and all 14 previously settled picks were verified unchanged; deployed HTML/JavaScript/CSS matched the source. The committed snapshot was refreshed from this verified public deployment.

## Streamlined update controls

The public collection schedule is now every six hours (05:17, 11:17, 17:17, 23:17 UTC). Snapshot metadata and the workflow cron are checked together. Eleven public-export tests passed. Desktop/mobile browser checks covered local-time/DST scheduling, direct manual-run navigation, queued/running/success status, one-time automatic reload after completion, a public-API failure fallback, date/sport preservation and no viewport overflow or JavaScript errors. Manual collection still uses GitHub’s authenticated Run workflow control; the public page reads status only.

The full GitHub check and deployment passed. Live HTML/JavaScript/CSS matched the source, the public snapshot advertised the four six-hour UTC slots, and the unauthenticated GitHub status API returned a successful run with the required public CORS header. The checked-in fallback snapshot was refreshed from the verified deployment.

### Player-prop research release

Added optional ESPN final-box collection and a custom-line research tab for NBA/WNBA, MLB, NFL and NHL. Initial verified public collection: 442 NBA players/92 games; 219 WNBA/201; 1,007 MLB/320; 504 NFL/120; 815 NHL/231. These are bounded source observations, not complete league logs or live betting markets. The public fallback retains the previously deployed team-model snapshot and adds only newly collected public player observations.

Validation: full existing-plus-prop suite passed (150 tests, 140 seconds); after adding corrupt-optional-cache recovery, the focused props/public-export suite passed all 16 tests. Browser checks passed at 1440px and 390px, including real-log selection across all five sports, custom line grading, pushes, Wilson interval bounds, empty data, shortlist add/remove and persistence, no horizontal overflow, and no browser exceptions. Synthetic test results were never published. No winner-model weights, retrospective performance scores or saved picks were changed by this feature.

A final parsing check also covered legitimate negative NFL yardage, which must remain in the denominator. The NFL parser cache is versioned to prevent reuse of earlier unsigned-only observations. Recollected NFL boxes contain 509 players across 119 games; the focused props/public-export suite passed 17 tests before cache-key versioning.

### Automatic game-specific Prop Finder

Added a dedicated top-level finder tab and direct `?view=finder` URL. Uses a fixed alternate-threshold catalog and both historical teams from a verified upcoming fixture. Count selection and Show all operate on the finite qualifying set without padding. Historical Beta(2,2) consistency scores are explicitly unvalidated, not next-game predictive probabilities; current roster, role, injury and bookmaker-line limitations are visible. Saved suggestions share the existing browser-local shortlist without the former 20-item cap.

Validation: all 17 public export/prop ingestion tests passed; five Node tests cover shrinkage, threshold selection, current-team/sample requirements, stale/past events, future-observation exclusion, missing statistics, recent-form veto and insufficient evidence. Those Node tests now run in both verify and deployment workflows. Browser checks at 1440px and 390px in America/New_York used actual deployed public logs/fixtures, found 97 qualifying candidates at 60%/Both settings in the inspected matchup, and verified 1-result, Show all, over-request/no-padding, invalid count, empty game, high-threshold empty state, saving and direct-link navigation. No overflow or browser exceptions. Threshold counts are exploratory, not backtest performance. No team-model weights or outcomes were altered; the checked-in fallback was synchronized from the verified live six-hour deployment.

### Injury coverage, explanations and actual right/wrong record

Verified ESPN public injury reports for NBA (100 listed players), WNBA (49), NFL (800), MLB (183), NHL (128) at collection. CFB returned only stale historical entries and was correctly marked unavailable. Reports are timestamp-checked, archived with hashes outside the website, and expire after eight hours. Prop Finder requires current coverage and excludes reported unavailable/uncertain statuses and injury-report team mismatches. Absence from the feed is not active-roster or starter confirmation.

Every team forecast now carries injury context and a baseline probability label; affected cards flag injury review. No arbitrary numeric injury penalty or accuracy claim was introduced. Immutable first-observed pregame injury features now accumulate independently for prospective research; after 200 settled events per league a fixed chronological logistic comparison runs, with no production promotion. Position-specific tests ensure NBA guards are not treated as NHL goalies. Original team-model parameters and saved winner picks remain unchanged.

Added a plain-language Why [team]? section using available fitted log-odds contributions and descriptive team context, plus expandable reported-player tables. A compact correct/incorrect/pending/observed-accuracy panel links to Right / wrong. Seven-calendar-day history includes today, while retaining actual first-published picks and separate policy records.

Validation: full suite passed 157 tests (135.74 seconds) before adding the final chronological-research and injury/export integration cases. The final focused suite passed all 24 injury/public-export/prop tests, including the missing-start guard; seven Node finder tests passed. Browser checks at 1440px/390px verified real injury tables, actual factor explanations, injury-filtered candidates, no overflow/exceptions, and today's correct/incorrect/pending/50% denominator with browser-only synthetic fixtures (never published). Retention is bounded to 180 days for raw injury archives; frozen research observations are retained separately.

### Hourly automation

Changed Pages collection/publication to cron `17 * * * *` and renamed the workflow Hourly model dashboard. Exported UTC slots now contain all 24 hours, with the same :17 minute; dashboard next-run calculation, workflow controls, runtime step summary and current operating docs agree. Existing public model outputs were synchronized from the verified deployment before changing schedule metadata. Model selection, sealed tests, injury guards and loss-triggered promotion policies remain unchanged.

Validation: 12 public-export tests and seven finder tests passed. Schedule checks covered before/exactly-at :17 and midnight rollover. A browser check confirmed the displayed next update is within one hour with no JavaScript errors. GitHub scheduled runs can be delayed; browser snapshot polling remains every minute.

### Bounded continuous improvement and deeper loss assessment

Reviewed scikit-learn temporal-validation/calibration documentation and River's ADWIN documentation. Implemented fixed error-adaptive features, recency-weighted regularized logistic candidates, chronological calibration and Bayesian/adaptive probability blends. The new catalog contains 21 candidates per sport plus a modern NBA development study (168 specification evaluations in the initial offline run). Original final-test boundaries were excluded. Each study compares against the prior development research winner; a higher raw accuracy that worsens log loss/Brier does not qualify. Cache fingerprints include the catalog, reference, development source hash and sealed-test boundary.

Real WNBA development evidence: same 638 games and development source hash as the prior published study; correct picks 442→445, accuracy .6927899687→.6974921630, log loss .6085960373→.6060433969, Brier .2096427080→.2088873110. Binned calibration error rose .0480→.0586; improved proper scores are not claimed as proof of better calibration. This is modest development selection evidence only. NBA/NFL/NHL/MLB/UFC retained prior choices; local CFB also retained its choice but its runtime cohort differs from deployment, so the fallback marks that study pending until the hourly job recomputes on deployed history. Modern NBA retained the current feedback specification. No new 70% or overall live-accuracy improvement is claimed.

Added a separate immutable, loss-triggered adaptive trial lane with frozen reference checksums, archival of superseded trials, and the existing 100-results/eight-calendar-weeks, log-loss/Brier/accuracy and paired-block promotion gate. Primary and NBA feedback trials also now exclude the actual creation date when evaluating future confirmation: backfilled older results cannot inflate prospective evidence. The historical test fixture's clock was made explicit to test genuine future games rather than late-imported past games. Original published picks remain immutable.

Added rolling 10/25/50/100 saved-pick metrics, confidence gaps, high-confidence misses, team/venue patterns, binned reliability/resolution with residual, and last-50-vs-previous-50 weekly-block drift diagnostics. These are descriptive investigation signals, not causal attribution, formal ADWIN results or permission to bypass promotion rules. The initial checked-in dashboard uses retained public history for diagnostic fallback; hourly builds compute the full current-policy ledger.

Validation: latest full suite **170 passed in 144.28 seconds**; focused new-feature/diagnostic/lifecycle suite **21 passed**; all seven Node prop tests passed. Tests cover temporal leakage, same-date batching, UFC score encodings, probability normalization/joblib restoration, sealed-period cache invariance, loss-triggered freezing, reference invalidation, independent-gate promotion, immutable ledgers, and backfill exclusion. Browser checks at 1440px and 390px verified actual study tables, modern-NBA status, WNBA development evidence, rolling/error diagnostics in Model lab and Right / wrong, no overflow and no browser exceptions. Synthetic gate/drift fixtures were never published. Details and online references: docs/CONTINUOUS_LEARNING.md.


Verified production deployment **41562023417** completed successfully. All seven adaptive reports contain 21 new candidates and match their deployed benchmark's sealed-test boundary. The WNBA frozen trial is collecting evidence with its cutoff on/after the actual creation date. Full policy diagnostic counts at verification: NBA 77, NFL 27, NHL 78, CFB 105, WNBA 3, MLB 5, UFC 16. Champion training SHA-256 values and original sealed test metrics matched the pre-change public snapshot; all overlapping saved picks retained their original probabilities.

Corrected the offline CLI to adopt the deployed sealed-test boundary when a local initial report differs. The initial exploratory local CFB result was discarded; the rerun respected the deployed boundary and still retained the prior choice. Canonical study artifacts and the checked-in fallback snapshot were then synchronized from the verified production deployment, replacing the pending/local-cohort fallback with the actual deployed CFB study. This follow-up changes offline boundary selection and evidence only; the verified live research/promotion logic is unchanged.

### Focused NBA development and verifiable injury capture

Confirmed the published NBA injury feed had 93 listed players with source/capture timestamps; the published injury research had zero settled observations, so no numerical injury adjustment was represented as learned. Added saved/pending/all-settled/current-schema counters, archived-report count, first/latest capture times, and a bounded recent-capture audit view. New NBA snapshots preserve the actual listed players and their prior observed points/rebounds/assists (last ten same-team appearances within 30 days, strictly before capture), separate uncertain-status production, and explicit missing-production/sample flags. Player-aware schema v2 does not retrofit old snapshots or silently mix their feature widths. Ledger updates are atomic, corrupt history is preserved for recovery, and new raw payload archives are compressed with timestamp/hash verification.

The 24-candidate modern NBA study tested season-history maturity, shared uncertainty, chronological calibration and retained-feedback blends. Selected calibration gained two development wins (1814→1816/2726, .6654438738→.6661775495), with modest log-loss/Brier improvements, but historical follow-up fell 904→888/1322 (.6838124054→.6717095310) and worsened both probability scores. It was rejected. The already-reused historical follow-up is not fresh independent evidence. No live NBA accuracy gain or arbitrary injury penalty is claimed; the retained model and existing trials remain protected.

Diagnosed failed follow-up workflow **41562631909** through its build log: the adaptive variant could be trained/locked but production `model_features` omitted it from its explicit allowlist. Added `context_feedback` and the new `context_nba_context` family; experimental box-score variants remain excluded. New regression tests serialize a real fitted challenger and evaluate it through production `probabilities`, covering the missing second-run path that previous building-only/mocked-trial tests did not exercise.

Validation: full suite **178 passed in 135.80 seconds** before adding the final failed-confirmation control test; the final focused NBA/injury/public-export/adaptive suite passed **36 tests**. Seven Node prop tests passed. Browser checks at 1440px and 390px verified rejection/evidence tables, injury recording counters and schema explanation, no document overflow and no JavaScript exceptions. Synthetic fixtures were never published. Details: docs/NBA_DEVELOPMENT.md and artifacts/research/nba-context-v1.json.

Verified repaired production workflow **41578408677** completed successfully, including full inference of the previously locked adaptive challenger. NBA publication contained 93 listed injury players, 4 archived reports, 15 first-observed pregame captures, 15 pending and zero imported settled outcomes. All 15 were older count-only snapshots; zero were retroactively converted into player-production records. The tracker now states the active schema and player-aware count explicitly. New player-aware capture begins on new eligible fixtures. Recent exported capture times preceded their verified event starts. NBA champion digest and original sealed test metrics matched the pre-change snapshot; the new 24-candidate study failed historical checks and did not open a replacement NBA trial. The WNBA adaptive trial remained collecting evidence. The final fallback and NBA study artifact were synchronized from this verified publication; desktop/mobile tracker checks passed again with the actual counters.

### Accurate prediction accounting and published future fixtures

Fixed final-result matching by canonical provider ID and validated opponents before comparing dates. Shared matching now settles the live policy ledger and public history despite local/UTC date differences; explicit NHL aliases and neutral UFC orientation are supported. Conflicting event results and wrong doubleheader IDs cannot silently grade a pick. Added recent-event final/status checks from verified public sources, retaining cached finals on temporary failure. Official start corrections exclude genuinely post-start records instead of awarding wins. Injury-label settlement similarly excludes snapshots outside the verified pregame window and distinguishes unscored outcomes.

The main seven-day record now counts one event once, preferring its current-policy first saved prediction without choosing the winning version. All original policy versions remain auditable. Future scheduled games are excluded from unfinished history; pending/in-progress, awaiting-source and unscored outcomes are separated, with accuracy restricted to decisive verified grades.

Real-source checks verified previously unresolved NBA `401909893` (Atlanta 114–Cleveland 111, source UTC date one day later than saved date) and WNBA `401918310` (Atlanta 80–Golden State 69). Other inaccessible or removed events were left unresolved. The real-data browser preview's NBA seven-day cohort contained 51 unique games (30 correct, 21 incorrect), rather than 102 policy versions, with zero unresolved NBA entries. These are accounting corrections, not a model-accuracy improvement claim.

Expanded future fixture collection to a rolling 365-day calendar as providers publish schedules. NBA season CSV returned 1,093 upcoming fixtures through 2027-04-12 UTC; NFL uses its published schedule, MLB crosses calendar-year boundaries, NHL merges full club seasons and near-date feeds, and CFB/WNBA attempt optional next-season schedules. Calendar-only exhibitions/conditional games never enter validated training or receive probabilities. Both team forecasts and prop suggestions remain within the guarded 14-day forecast window. Added Published game dates, Next games and paged all-upcoming browsing; generated asset URLs include content fingerprints to avoid stale counting/navigation code.

Validation: full Python suite **189 passed in 142.44 seconds** before the final MLB year-boundary regression was added, final focused grading/export/feed/injury suite **38 passed**, and **12 Node tests passed**. Tests cover date-independent identity, opponents and doubleheaders, neutral orientation, final status validation, corrected start exclusion, cached-final preservation, future legacy starts, unique-game policy selection, denominator categories, distant schedules, preseason training exclusion and NHL deduplication. Browser checks at 1440px/390px used actual published picks, independently verified finals and the real NBA future calendar: confirmed unique counts, original-policy audit, next-date jump, March 2027 selection, paged upcoming rows, guarded distant props, no overflow and no browser errors. No synthetic predictions were published. Details: docs/PREDICTION_RECORD.md.

## NBA schedule/form and all-sport outcome learning

Added 12 NBA schedule/form candidates to the fixed 24-candidate context study. Development selection: 67.058% versus 66.544% accuracy on 2,726 events. The selected candidate failed the later historical confirmation (67.927% versus 68.381%, 1,322 events; both proper probability scores worsened), so it is not eligible for live promotion. Evidence is in `artifacts/research/nba-context-v2.json`; no new production accuracy gain is claimed.

Adaptive trials now accept a newly settled correct result as well as a loss, while retaining frozen independent trial evaluation and promotion gates. Tests cover all seven leagues' causal feedback, NBA schedule compression/offseason reset, model serialization/live inference, correct-result trial creation, and both directions of upset accounting with unscored exclusions. Focused checks: 34 passed. Browser checks passed at 1440px and 390px for all six sections, selected navigation state, explanatory text, expandable research, sport switching and horizontal overflow. JavaScript regression checks: 12 passed.

## Across-team 100% observed prop rates

Added a separate Players → 100% hit rates section, defaulting to all sports and all teams without a fixture requirement. It requires a complete last-5/10/20 collected-statistic sample and literal hits/sample = 1; the shrunk estimate remains below 100%. Shows observed team, sample dates, all supporting values, separate availability, collection time, and historical uncertainty. The scan excludes future observations, stale latest appearances and incomplete samples. Source collections must be checked within 24 hours. Display paginates 50 at a time.

JavaScript regressions: 15 passed, including cross-team results, perfect overs/unders, short samples, missing/future observations and stale logs. Desktop/mobile browser checks passed at 1440px and 390px with an explicitly synthetic UI-only record (never exported), proving no team selection is required, sample filters work, tab visibility is correct and no page errors/overflow occur.

## Best daily props across games

Players → Best props today now defaults to all supported sports and all upcoming games on the selected local date. The count applies to the combined, evidence-ranked pool, with Show all available and an optional literal 100% observed hit-rate filter. Optional sport/game filters remain available. Cards identify sport, matchup and kickoff time; saved suggestions retain the actual sport instead of the All sports selector value. Existing fresh-feed, 24-hour player collection, injury-availability and 14-day research-horizon requirements remain enforced.

JavaScript regression checks: 17 passed. Added aggregate tests for cross-sport ranking, duplicate-fixture handling, missing injury coverage and perfect-history filtering. Synthetic UI-only browser checks passed at 1440px and 390px: all-games default, requested count, Show all, perfect filter, sport-correct shortlist, individual-game filter and no overflow/errors. Synthetic records were never exported.

## Historical stat targets instead of required over/under

Best props for the day now computes the highest observed statistic total reached in at least the chosen fraction of the full selected last-5/10/20 collected appearances. The default is 90% over 10 appearances; equality counts. For descending values 35, 30, 29, 28, 26, 25, 24, 23, 22, 15, the target is 22+ points (9/10), not a catalog sportsbook line. A 100% requirement gives 15+ (10/10). Fractional sample requirements round up; ties can produce a higher actual hit rate. Zero/negative targets remain explicit rather than inventing a positive floor. This is an empirical historical quantile, not the most likely next-game value or a calibrated probability.

The daily finder removes its required Side control, adds a target historical hit-rate selector and optional player search, retains all-games ranking/count controls, and displays inclusive hit/miss evidence. Other custom-line and historical-perfect sections retain their existing purpose. Full requested windows, source freshness and injury checks remain required.

JavaScript checks: 20 passed, covering maximal inclusive targets, ties, fractional values, zeros/negative totals, ceiling sample counts, full windows and all-game integration. Desktop/mobile UI checks verify no Side control, default 90%, a derived 22+ / 9-of-10 result, 100% changing it to 15+, counts, shortlist and game filters. UI fixture records are synthetic and never exported.

## Today-only props and all-state daily calendar

Added a separate daily ESPN calendar across all seven sports. Each hourly build fetches the Eastern calendar date and following date individually, then filters event start times to the Eastern day. Includes pregame, in-progress, completed, postponed and other published states without adding any such events to training or forecast input. College football requests all FBS groups. This independent calendar also supplies the selected-day schedule table and sport counts; it does not replace the existing future schedules.

The daily prop finder always uses today in the viewer's local day (Eastern for this user), even when browsing a different forecast date, and keeps started/completed games in its game selector. Started-game research explicitly opts into past fixtures; all statistical observations must still precede game start. Recalculated research targets are labeled and never represented as original saved pregame picks. All target totals of zero or less are excluded, with no replacement value invented.

Source verification on November 8, 2026 (Eastern): all seven calendar requests succeeded; NBA 7 events, NFL 13, NHL 6, and zero returned for WNBA/CFB/UFC/MLB. This is provider calendar coverage, not a guarantee against provider omissions. Tests cover UTC/local midnight boundaries, all statuses, deduplication, source query/persistence, pre-start statistical cutoff, and zero/negative target exclusions. JavaScript checks: 22 passed. Browser checks at 1440px/390px verified today-only behavior after selecting tomorrow, continued display of in-progress/final/upcoming games, game statuses, positive-only stat targets and no errors/overflow. Synthetic browser fixture data were not exported.

## Injury matching and lifetime prediction accounting

Fixed injury-context matching when NFL/NHL schedule opponents use abbreviations but injury reports use full names. Injury context now includes explicit affected players and a coverage/review status. Prediction cards flag affected matchups as an unadjusted baseline, and matchup explanations use the resolved team reports. Numerical injury effects remain unvalidated and are not represented as an approved adjustment.

Every newly saved pregame pick now freezes its injury context and availability note alongside its original probability. Later refreshes cannot overwrite that original pick or injury snapshot. Lifetime accounting reads the full retained ledger, independently of the eight-day history export, deduplicates canonical event identities across policies, and uses the earliest valid saved pregame pick. Both wins and losses count; scheduled, unresolved, canceled, draws and invalid entries do not affect accuracy. Per-sport and all-sport weighted averages are exported separately from recent-policy and sealed historical test accuracy. Predictions that were never recorded cannot be reconstructed retroactively.

The hourly workflow backs up only public lifecycle state ledgers as downloadable GitHub artifacts retained for 90 days, in addition to its working cache. New tests cover old saved games, persisted outcomes, duplicate policy wins not replacing original misses, invalid entry handling, unfinished-game denominators, immutable injury/probability snapshots, and NFL/NHL injury aliases. Focused Python checks: 28 passed; lifecycle-inclusive checks: 33 passed before the alias test addition. JavaScript checks: 22 passed. Desktop/mobile checks at 1440px and 390px verified the lifetime section and combined average. Browser fixture records were synthetic and never exported.

## Live-update, recorded-outcome and props-layout audit

Verified successful recent hourly workflows and the deployed snapshot generated November 8, 2026 at 23:46 UTC (6:46 p.m. Eastern): all seven feed statuses fresh. Downloaded the public prediction-ledger artifact from successful run 42536422149 and independently summed original ledger outcomes. Every sport exactly matches its published all-time record: NBA 86/46 correct/incorrect, NFL 24/13, NHL 80/47, CFB 115/56, WNBA 2/3, MLB 3/2, UFC 12/8. Combined: 322 correct, 175 incorrect, 497 graded (64.7887%). Scheduled/unresolved games are excluded; no missing historical forecast was reconstructed.

Added public all-time prediction archives with 7-day, 30-day and all-recorded period controls, preserving original probabilities and actual outcomes for inspection. Lifetime records now include saved-probability log loss and Brier score, both aggregated across sports by graded sample size. Snapshot health summarizes fresh feeds, graded/unresolved counts and reconciliation status. Older unresolved predictions are now retried beyond the prior ten-day limit; verified old final/canceled/postponed records survive cache retention. Recent checks receive 200 slots and older checks 50; failed sources do not invent outcomes.

The older November 4 workflow 41926867985 completed its data/model build but timed out in deployment. Increased the deployment timeout to 15 minutes. GitHub Pages still uses legacy branch deployment in addition to the custom Actions deployment. Attempting to switch the repository Pages source to workflow returned HTTP 403 (integration lacks permission); the repository owner must select Settings → Pages → Build and deployment → Source → GitHub Actions. Recent custom deployments succeed despite this unresolved configuration issue.

Simplified player navigation to Daily targets / Perfect records / Game logs, separated primary daily-target controls from expandable optional filters, grouped actions and aligned responsive controls. Focused backend checks: 24 passed; JavaScript checks: 22 passed. Desktop/mobile checks at 1440px and 390px verified all-recorded historical outcome rows, count and positive-target filters, shortlist behavior, optional filters, game statuses and no errors/overflow. Synthetic UI fixtures were never exported.

## Stat slider and priority model reviews

Added a draggable player-stat target with live observed hits/graded sample/rate, selected-window Wilson interval, 80/90/100% empirical presets, recent-value bars, keyboard access, manual input and browser-local saved supporting counts. Daily cards open the builder with the correct player/stat/game, freezing the research cutoff at game start. Unit cases check inclusive equality versus over/under pushes, slider thresholds changing 9/10 to 2/10 hits, sorting/deduplication, future/game-time exclusion and full window handling. JavaScript checks: 24 passed. Desktop/mobile browser checks at 1440px and 390px cover slider input, presets, keyboard, positive-only targets, saved 9/10 provenance, game-linking and model-review display. Synthetic browser records were never exported. Online methods reviewed are linked in `docs/STAT_BUILDER.md`.

Model priorities are NFL first, NBA second, NHL third. Added an hourly saved-prediction review with confidence bands, worst-loss teams and a fixed 15-candidate temperature/home-bias calibration grid selected only on earlier saved results and checked on later results. These descriptive reviews never change production weights or bypass the existing future gate. Tests verify later outcomes cannot choose the specification and duplicate policy versions cannot inflate the sample.

Evidence frozen from public snapshot 2026-11-09T00:13:41Z: NFL 24/37 correct (64.86%), NBA 86/132 (65.15%), NHL 80/127 (62.99%). NBA's development-selected softening reduced later-check accuracy from 37/50 (74%) to 36/50 (72%) and worsened probability scores, so retain existing probabilities. NHL's candidate reduced later-check log loss 0.637639→0.634812 and Brier 0.223328→0.222884 but accuracy fell 30/47→29/47, so retain existing probabilities. NFL lacks enough distinct saved game dates for the same chronological study. Injury samples: NBA 33, NFL 10, NHL 47 settled, all below the 200-observation research minimum. No injury adjustment or live accuracy improvement is claimed. Full machine-readable evidence is in `artifacts/research/priority-saved-predictions.json`.

Complete Python suite for this update: 211 passed in 146.28 seconds. Focused priority/export checks: 16 passed; JavaScript regression checks: 24 passed. Direct view links are now supported for the stat builder and model reviews as well as the daily finder.

## Feed and storage audit

See `docs/STORAGE.md` for measured sizes, source/backup retention and provider-specific injury availability. Added tests for lossless SHA-256-verified compression, archive deduplication, cache byte caps, protection of databases/models/ledgers/player logs, preservation of unknown/mismatched files, injury-archive retention, seven-backup retention, and backup/restore provenance with authentication excluded. Focused storage/feed/export checks: 25 passed. Real runtime cleanup reduced storage by 182,024,270 bytes without deleting source or injury archives; protected hashes and actual backup restoration were verified.

Concurrent identical downloads were additionally tested to ensure a single valid gzip archive is retained with no temporary-file race. Final focused storage/feed/export checks: 26 passed. JavaScript regression checks: 24 passed.

## Faithful interpretation and daily scoreboard UI

Added verified probability-point effects for standardized logistic/Elo models, including the known rest-guard wrapper. Tests confirm log-odds reconstruction, exact agreement with direct model reference predictions, contribution ranking, ignored metadata handling and fail-closed behavior for unsupported/mismatched models. Matched local champion weights reconstructed 102 NBA, 28 NFL and 102 NHL published forecasts without changing their probabilities. New picks save their top-three effects; older picks remain untouched.

Added a daily scoreboard inspired by the supplied examples: source scores/status, first-saved probability bars, correct/incorrect badges, all-time record summary, allowlisted logos/monogram fallbacks and accessible detail dialogs. Tests cover earliest-pick selection, post-start rejection, team identity, NFL aliases, cross-provider game times and MLB doubleheader ambiguity. No unsupported market odds or retrospectively generated picks are shown. All previous tools/views remain available. Daily source parsing now exposes scores only for started/completed games and sanitizes logo URLs.

Focused backend checks: 24 passed; JavaScript checks: 26 passed. Desktop/mobile checks at 1440px and 390px passed for real-model explanations, ranked effects, technical details, scoreboard scores/bars, correct/incorrect/no-pick states, historical dialog behavior, Escape dismissal, existing stat slider and no errors/overflow. Synthetic scoreboard test records were never exported. Refer to `docs/INTERPRETATION.md` for methods and the latest failed calibration tests; no live weights changed.

Full Python suite: 221 passed in 140.11 seconds. Final focused interpretation/daily-calendar/export checks: 20 passed; JavaScript checks: 26 passed. Model readiness and archival dataset metrics remain available in an expandable section to reduce initial-page clutter; existing navigation and tools are preserved. Logos fall back to monograms on load failure. The scoreboard only scans the selected day's archived/current forecasts, reducing repeated matching work without changing probabilities.
