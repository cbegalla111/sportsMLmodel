# Setup, updating and recovery

Use the existing isolated checkout. Do not create a Git worktree for a cloud task.

## Working preview

Use the [one-click Codespaces setup](PREVIEW.md) for automatic startup and private forwarding. Existing cloud paths remain compatible; install/start scripts now resolve the checkout location and honor SPORTSLAB_VENV and SPORTSLAB_HOME overrides.

## Install / run

Python 3.12; exact scientific dependency versions in requirements.txt. On the cloud machine:

```bash
cd /workspace/sportsMLmodel
bash scripts/install.sh
bash scripts/start.sh
```

The app binds to loopback port 8765 by default. This is a local service, not a deployed URL. Password authentication is required for all data and mutation endpoints. The random password is generated in `/workspace/.sportsml-private/initial-password.txt` (mode 600); retrieve it privately on your own machine, never commit it or post it in chat. It is stored as a salted PBKDF2-SHA256 hash. Delete the initial-password file after storing the password in your password manager; keep auth.json so the password remains valid. To rotate, stop the service, securely remove auth.json and the initial-password file, restart, and retrieve the new password. Sessions expire after eight hours and are intentionally invalidated by restarts. Login attempts are rate limited. JSON mutations require session CSRF tokens and same-origin requests.

`SPORTSLAB_HOME` controls the private data root. The SQLite database, settings, forecasts, experiments, model artifacts, raw source hashes, feed attempts and backups live there. Credentials are never placed in frontend code. OS directory permissions protect local state. SQLite and backup archives are not encrypted at rest: use an encrypted disk and restrict backup access.

## Automatic updates

The start script supervises the web process and a six-hour refresh worker. If either exits, both stop; a container restart policy restarts them on a real host. Future cloud tasks must restart both; live processes do not survive publication snapshots. Logs: `$SPORTSLAB_HOME/refresh.log`.

```bash
/workspace/.sportsml-venv/bin/python -m scripts.refresh
/workspace/.sportsml-venv/bin/python -m scripts.refresh --watch --interval 21600
```

The worker:

1. Fetches NFL public schedules/results (season >=2005), current-season NBA CDN results/schedule, MLB history from 2024 on initial seed and the current year thereafter, and a rolling NHL schedule window. Initial installation backfills NHL weekly official schedules from October 2024 when history is insufficient.
2. Archives exact source bytes, hashes and fetch times; imports only supported result fields, refusing conflicting revisions. Feed failures retain old data and are visible in the UI.
3. Imports CSV files dropped into `$SPORTSLAB_HOME/inbox`; accepted files move to processed, rejected files to rejected with an error reason. Write temporary files elsewhere and atomically rename completed CSVs into inbox.
4. Refits weights only for a previously selected frozen model when its data digest changes. It does not invent or automatically validate models for empty leagues. For a new league, run `python -m scripts.train --league MLB` (or UI comparison) once sufficient data exist. UI comparison returns existing results for an unchanged dataset; changing an already evaluated league does not restart selection.
5. Makes one consistent private backup daily, retaining seven local copies. Local backups do not protect against machine loss. Copy them to your own encrypted off-machine storage.

Verified feeds: NFL, MLB Stats API and NHL API. MLB regular-season/postseason filtering excludes tied preseason games; a regression test covers that case. NHL historical backfill and rolling schedule updates were exercised. The saved domain additions (cdn.nba.com, statsapi.mlb.com, api-web.nhle.com) became effective during setup and MLB/NHL requests succeeded. Current NBA CDN endpoints still return origin HTTP 403, so current NBA results/schedules are unavailable; the archived NBA source ends in June 2015. Keep failed-feed status visible and do not treat a successful DNS/network change as data readiness.

CFB/WNBA/UFC have no verified credential-free connector in this implementation. Use a documented, permitted CSV export or manual entry; drop recurring exports into inbox for automatic ingestion. No credential or paid-service requirement is invented. Advanced pregame data, confirmed availability and live odds are not automatically supplied. Different source identifiers and neutral-site conventions must be reviewed before mixing datasets; the first current NBA source is a separate source namespace.

## Backup / restore

```bash
/workspace/.sportsml-venv/bin/python -m scripts.backup /workspace/sportsml-backups
/workspace/.sportsml-venv/bin/python -m scripts.restore /path/to/sportslab-TIMESTAMP.tar.gz /workspace/.sportsml-restored
```

Backups include a SQLite-consistent database copy, models, source archives and checksum manifest. Authentication secrets and sessions are excluded. Restore requires a new/empty destination, rejects unsafe archive paths and verifies file hashes and SQLite integrity. Set SPORTSLAB_HOME to the restored directory and start the service; initialize a new password. User CSV originals in inbox/processed/rejected and logs are not included in these archives; their accepted normalized records and provenance are in SQLite. Keep original exports separately if required.

Source recovery: clone the GitHub repository, install pinned dependencies, restore a private backup, then restart. Committed artifacts contain actual benchmark reports, held-out predictions and the selected full-history model weights for NBA/NFL/MLB/NHL; they contain no passwords. `scripts.seed_models` can restore benchmarks only when historical imported data match their saved digest. If a feed revises old results, it refuses to silently validate a different dataset. Saved installation/startup instructions are a configuration draft, not publication. Publish the cloud environment through its settings to retain the prepared filesystem snapshot.

## Private hosting

GitHub stores source and model artifacts; GitHub Pages cannot run the Python server, SQLite or scheduled worker. No remote deployment has been performed.

A Docker recipe is included. Normal in-container package fetching hit DNS restrictions in this cloud environment; the optional wheelhouse cache supports verified offline builds (see wheelhouse/README.md). An offline build, the in-container test suite, and the running authenticated service were verified here. No remote hosting was performed. On your server:

```bash
docker compose up --build -d
# Seed historical NBA data, fetch available feeds and restore verified benchmarks:
docker compose exec lab /workspace/.sportsml-venv/bin/python -m scripts.import_nba
docker compose exec lab /workspace/.sportsml-venv/bin/python -m scripts.refresh
docker compose exec lab /workspace/.sportsml-venv/bin/python -m scripts.seed_models
```

Compose publishes only to the server's loopback interface and persists /data in a volume. Reach it through an authenticated SSH tunnel: `ssh -L 8765:127.0.0.1:8765 YOUR_SERVER`. Then open the local service in your own browser and sign in. Do not bind a bare HTTP service publicly. A browser-accessible private domain requires a host and TLS reverse proxy; set SPORTSLAB_SECURE_COOKIE=1 behind HTTPS, configure the proxy to preserve Host, and verify both authenticated access and anonymous rejection before using it. The application login remains required. Do not enable public hosting without the user's explicit authorization.
