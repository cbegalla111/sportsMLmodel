# Public dashboard and daily model updates

The user explicitly approved a public GitHub Pages dashboard on October 21, 2026. This is separate from the original private Python workbench.

Public website: https://cbegalla111.github.io/sportsMLmodel/

## What the website displays

- Seven sport views: NBA, NFL, NHL, CFB, WNBA, MLB and UFC. Forecasts, Model Lab, and Data & Sources sections stay separate within each sport.
- Real public result counts/coverage; descriptive rolling team statistics; latest 20 imported final results; exact source/check timestamps; missing-input status.
- Limited statistics-only forecasts for source-backed fixtures when fresh inputs and validated model lineage exist. Rank by the larger opponent win probability, filter by event date, and inspect model factors, raw input differences and the dataset/version audit trail.
- Actual archived chronological model comparisons, final-test log loss/Brier/accuracy/AUC, reliability diagram with bin counts, season breakdowns, and approximate block-bootstrap Brier intervals.
- Explicitly empty forecasts when a league lacks sufficient verified data, a source fails, the current dataset differs from archived benchmark lineage, a team lacks recent history, or an event has begun. No demonstration results substitute for missing content.

All seven sports have daily result/schedule connectors. NBA uses the SportsDataverse/hoopR mirror of ESPN schedules; WNBA/CFB/UFC use the ESPN scoreboard; NFL/MLB/NHL retain their established providers. Current coverage and validated model status are reported per sport. Starting pitchers, goalies, injuries, lineups and advanced efficiency features are not supplied or claimed validated.

## Daily operations

`.github/workflows/pages.yml` runs:

- Daily at **11:17 UTC** (7:17 AM in New York during daylight saving, 6:17 AM during standard time).
- On every push to main, or manually via **Actions → Daily model dashboard → Run workflow**.

The job installs exact dependencies, runs tests, restores its public-data cache, downloads available results and schedules, reviews losses and prospective challengers, generates forecasts, and deploys ONLY the public `_site` bundle to GitHub Pages. Data/model counts and source status are written into the run summary. Historical backtest scores stay sealed and are never tuned repeatedly by the daily job. Champion weights are retained until the independent promotion gate passes. No sportsbook-derived features are ingested.

A source-verified event start is used when available: NHL `startTimeUTC`, MLB `gameDate`, and NFL `gametime` converted from documented Eastern time with daylight-saving rules. The NFL definition is documented in [nflreadr's schedule dictionary](https://github.com/nflverse/nflreadr/blob/main/data-raw/dictionary_schedules.csv). Where only a date is available, same-day forecasts are withheld and future forecasts expire at that date's UTC midnight. Historical result dates retain source calendar conventions to preserve the archived benchmark inputs. The date-only feature engine may conservatively withhold a same-day forecast if other results already exist on that date.

A forecast also expires when its source check or published snapshot is 24 hours old. The browser checks for updates once per minute and hides probabilities after expiry or event start. Historical test metrics remain readable. GitHub schedules can be delayed or disabled; the website's expiry policy prevents overdue forecasts from silently appearing current.

The public workflow cache is separate from any user's private runtime. It retains public history between daily runs. On a cold cache, initial history is reconstructed from sources starting in 2004/2005/2024 as appropriate. Upstream revisions that invalidate the archived dataset hash withhold current forecasts for review instead of pretending the old validation still applies.

The private workbench's updater defaults to once per day too; start/restart it to apply that changed interval. Its explicit `--interval` override remains available. This process runs only while the private host is awake; GitHub's scheduled public job is independent of it.

## Privacy boundary

`sportslab/pages.py` reads only explicit public-source namespaces and source labels. It selects the result schema fields, excludes private/unknown uploads and extra uploaded fields, and ignores private model weights. It uses committed public benchmarks or a newly validated public-only initial model in an isolated temporary database. Champion and challenger artifacts are retained separately under public-lifecycle in the source cache. It never reads authentication files or exports personal prediction history/settings. Pure prediction estimation never writes the personal ledger. First published forecasts are recorded separately in the public-only lifecycle ledger for prospective scoring. Private data and raw source downloads are not included in the Pages artifact.

`_site` contains only index.html, .nojekyll, three web assets and web/data/snapshot.json. Unexpected files or symlinks in an existing output directory cause the build to refuse publication. The authenticated Python app and its API remain separate; public Pages is read-only and has no fake login, upload button, or on-demand training API. Public model outputs may be downloaded by anyone.

## Build and publish

```bash
# Build from an existing public-source runtime without changing its private ledger:
python -m scripts.build_pages --runtime /workspace/.sportsml-private --output _site
# Fresh standalone public source refresh + guarded review:
python -m scripts.build_pages --runtime .pages-runtime --output _site --refresh
```

The existing repository uses main/root Pages publishing. The custom GitHub Actions deployment was verified successfully with those existing settings; no settings change is required to use the daily job. Selecting **Settings → Pages → Build and deployment → Source: GitHub Actions** is an optional owner action to avoid redundant legacy builds. This integration cannot change that administrative setting. Every main-branch push also runs the custom publisher so a legacy build cannot remain the final outdated snapshot after a successful refresh. The scheduled custom workflow is the supported path for daily updates; it deploys generated data without committing data changes with a personal token. No API keys or paid data service is required for the currently verified public feeds. GitHub's runner supplies its own scoped deployment token.

Source code and the first public snapshot are committed. Daily later snapshots are built/deployed by Actions and need not produce source commits. The private runtime and personal ledger need separate backups; neither a public Pages deployment nor an Actions data cache backs those up.

## Feeds and guarded updates

All seven sports have scheduled connectors: NFL uses nflverse, MLB the MLB Stats API, NHL the NHL schedule API, and WNBA/CFB/UFC the ESPN public scoreboard, and NBA the SportsDataverse/hoopR schedule mirror of ESPN. Modern ESPN history is backfilled from 2022 by season (monthly for UFC); NBA uses the mirror’s full schedule CSV filtered from 2022; completed periods are checkpointed so interrupted imports resume. Responses are archived and hashed. Only final outcomes, scores and fixtures are selected; odds are ignored. These public endpoints have no service-level guarantee and can change or refuse requests.

The website is a daily snapshot, not a real-time play-by-play service. Each sport displays its provider, checked time, last successful connection, result coverage and upcoming fixtures. An off-season empty schedule is distinct from a failed source. The compact feed overview does not conceal source errors; Data & Sources contains connection details.

Daily runs settle the first published forecasts, review losses and evaluate locked challengers. They do not automatically change weights merely because a favorite lost. See METHODS.md for the prospective promotion gate. The public-only lifecycle cache retains champion/challenger weights, consumed confirmation windows and the public forecast record. GitHub Actions caches can be evicted; a cache miss restarts the public ledger and conservative review process from the archived benchmark, never inventing prior performance. Private uploads and personal prediction history remain outside the public cache.
