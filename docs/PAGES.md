# Public dashboard and daily model updates

The user explicitly approved a public GitHub Pages dashboard on October 21, 2026. This is separate from the original private Python workbench.

Public website: https://cbegalla111.github.io/sportsMLmodel/

## What the website displays

- Seven sport views: NBA, NFL, NHL, CFB, WNBA, MLB and UFC. Forecasts, Model Lab, and Data & Sources sections stay separate within each sport.
- Real public result counts/coverage; descriptive rolling team statistics; latest 20 imported final results; exact source/check timestamps; missing-input status.
- Limited statistics-only forecasts for source-backed fixtures when fresh inputs and validated model lineage exist. Rank by the larger opponent win probability, filter by event date, and inspect model factors, raw input differences and the dataset/version audit trail.
- Actual archived chronological model comparisons, final-test log loss/Brier/accuracy/AUC, reliability diagram with bin counts, season breakdowns, and approximate block-bootstrap Brier intervals.
- Explicitly empty forecasts when a league lacks sufficient verified data, a source fails, the current dataset differs from archived benchmark lineage, a team lacks recent history, or an event has begun. No demonstration results substitute for missing content.

NBA currently has only archived 2004–2015 results in this workspace; its current CDN returns 403. CFB/WNBA/UFC have no loaded verified historical dataset or fitted model. Their views explain coverage and sport-specific feature requirements. NFL/MLB/NHL have current public-source history and limited result-only forecasts. Starting pitchers, goalies, injuries, lineups and advanced efficiency features are not supplied or claimed validated. MLB's historical discrimination is modest and is reported honestly.

## Daily operations

`.github/workflows/pages.yml` runs:

- Daily at **11:17 UTC** (7:17 AM in New York during daylight saving, 6:17 AM during standard time).
- On relevant pushes to main, or manually via **Actions → Daily model dashboard → Run workflow**.

The job installs exact dependencies, runs tests, restores its public-data cache, downloads available results and schedules, refits frozen per-league specifications, generates forecasts, and deploys ONLY the public `_site` bundle to GitHub Pages. Data/model counts and source status are written into the run summary. Historical backtest scores stay sealed and are never tuned repeatedly by the daily job. Refitting current weights is not new held-out validation. No sportsbook-derived features are ingested.

A source-verified event start is used when available: NHL `startTimeUTC`, MLB `gameDate`, and NFL `gametime` converted from documented Eastern time with daylight-saving rules. The NFL definition is documented in [nflreadr's schedule dictionary](https://github.com/nflverse/nflreadr/blob/main/data-raw/dictionary_schedules.csv). Where only a date is available, same-day forecasts are withheld and future forecasts expire at that date's UTC midnight. Historical result dates retain source calendar conventions to preserve the archived benchmark inputs. The date-only feature engine may conservatively withhold a same-day forecast if other results already exist on that date.

A forecast also expires when its source check or published snapshot is 24 hours old. The browser checks for updates once per minute and hides probabilities after expiry or event start. Historical test metrics remain readable. GitHub schedules can be delayed or disabled; the website's expiry policy prevents overdue forecasts from silently appearing current.

The public workflow cache is separate from any user's private runtime. It retains public history between daily runs. On a cold cache, initial history is reconstructed from sources starting in 2004/2005/2024 as appropriate. Upstream revisions that invalidate the archived dataset hash withhold current forecasts for review instead of pretending the old validation still applies.

The private workbench's updater defaults to once per day too; start/restart it to apply that changed interval. Its explicit `--interval` override remains available. This process runs only while the private host is awake; GitHub's scheduled public job is independent of it.

## Privacy boundary

`sportslab/pages.py` reads only explicit public-source namespaces and source labels. It selects the result schema fields, excludes private/unknown uploads and extra uploaded fields, and ignores private model weights. It uses only committed public benchmark artifacts and refits them in an isolated temporary database. It never reads authentication files or exports personal prediction history/settings. Pure prediction estimation does not write either prediction ledger. Private data and raw source downloads are not included in the Pages artifact.

`_site` contains only index.html, .nojekyll, three web assets and web/data/snapshot.json. Unexpected files or symlinks in an existing output directory cause the build to refuse publication. The authenticated Python app and its API remain separate; public Pages is read-only and has no fake login, upload button, or on-demand training API. Public model outputs may be downloaded by anyone.

## Build and publish

```bash
# Build from an existing public-source runtime without changing its private ledger:
python -m scripts.build_pages --runtime /workspace/.sportsml-private --output _site
# Fresh standalone public source refresh + model refit:
python -m scripts.build_pages --runtime .pages-runtime --output _site --refresh
```

GitHub repository settings: **Settings → Pages → Build and deployment → Source: GitHub Actions**. The root index and committed initial public snapshot also replace the README when using legacy main/root publishing. The scheduled custom workflow is the supported path for daily updates; it deploys generated data without committing data changes with a personal token. No API keys or paid data service is required for the currently verified public feeds. GitHub's runner supplies its own scoped deployment token.

Source code and the first public snapshot are committed. Daily later snapshots are built/deployed by Actions and need not produce source commits. The private runtime and personal ledger need separate backups; neither a public Pages deployment nor an Actions data cache backs those up.
