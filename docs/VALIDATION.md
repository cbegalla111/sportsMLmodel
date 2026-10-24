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
