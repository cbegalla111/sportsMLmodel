# Courtside · Sports Prediction Lab

**[Open the public dashboard](https://cbegalla111.github.io/sportsMLmodel/)**

A detailed statistics-only sports dashboard, with a separate password-protected Python research workbench. The public GitHub Pages site shows actual model outputs; it does not run a Python server or expose private account data.

## Public dashboard

Seven sport views: **NBA, NFL, NHL, CFB, WNBA, MLB, UFC**. Each has Forecasts, Model Lab, and Data & Sources sections. Browse ranked source-backed matchups, conditional win probabilities, model factors, calibration plots, chronological comparisons, season scores, team statistics, recent results, freshness and missing inputs.

**Daily at 11:17 UTC**, GitHub Actions refreshes public history/schedules, refits frozen model specifications, exports current forecasts, and publishes the static dashboard. Main-branch pushes and manual workflow runs also rebuild it. Historical test scores remain sealed. Forecasts expire at verified event start or the conservative date-only cutoff, and are hidden when updates become overdue. [Daily update and privacy details](docs/PAGES.md).

| League | Historical decisive results | Held-out n | Selected specification | Log loss | Brier |
|---|---:|---:|---|---:|---:|
| NBA | 14,208 | 2,676 | logistic, 20-game window | 0.60827 | 0.21058 |
| NFL | 5,776 (plus 15 stored ties) | 1,048 | logistic, 10-game window | 0.63577 | 0.22275 |
| MLB | 7,413 | 1,462 | logistic, 20-game window | 0.68569 | 0.24628 |
| NHL | 2,932 | 441 | logistic, 20-game window | 0.67067 | 0.23889 |

These are archived benchmark sample sizes and results, not automatically updated validation claims. Current ingestion counts and daily training hashes are shown on the website. NFL/MLB/NHL have verified public feeds. NBA's archive ends in June 2015 and the current CDN is unavailable here. CFB/WNBA/UFC have no verified loaded data/fitted models; their pages show that honestly. Sport-specific advanced feature groups were skipped because complete inputs are absent. These limited result-history baselines are not injury-, pitcher- or goalie-aware models. MLB's predictive signal is modest. Probabilities condition on a decisive winner; NFL ties and UFC draws/no contests are excluded. No guarantee, sportsbook value, prop or parlay probability is invented.

## Private Python workbench

CSV/manual imports, immutable result history, SQLite settings/prediction ledger, model comparisons, scenarios, authentication/CSRF protection, daily source refresh and verified backups remain available in the separate Python app. No private upload, password, personal ledger or private model weights are exported to Pages.

```bash
cd /workspace/sportsMLmodel
bash scripts/install.sh
bash scripts/preview.sh start
```

The shell scripts resolve the checkout location and honor SPORTSLAB_HOME/SPORTSLAB_VENV overrides. Current cloud defaults preserve data in /workspace/.sportsml-private. Retrieve the generated password privately from its initial-password.txt file; never commit or share it.

For an editable private development environment, [open GitHub Codespaces](https://codespaces.new/cbegalla111/sportsMLmodel?quickstart=1). [Preview instructions](docs/PREVIEW.md) cover private forwarding, sign-in and browser refresh. The public website above requires no Codespaces session.

- [Public Pages dashboard and daily updates](docs/PAGES.md)
- [Setup, refresh, backup, recovery and private hosting](docs/OPERATIONS.md)
- [Data schema and outcome rules](docs/DATA_SCHEMA.md)
- [Methods, primary sources and limitations](docs/METHODS.md)
- [Actual validation evidence](docs/VALIDATION.md)

Public benchmark reports, exact held-out predictions and selected model artifacts live in artifacts/. Raw archives, private data and authentication stay outside Git. Keep an off-machine private backup; Pages and Actions caches do not preserve your personal ledger.
