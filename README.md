# Courtside · Sports Prediction Lab

**[Open the public dashboard](https://cbegalla111.github.io/sportsMLmodel/)**

A detailed statistics-only sports dashboard, with a separate password-protected Python research workbench. The public GitHub Pages site shows actual model outputs; it does not run a Python server or expose private account data.

## Public dashboard

Seven sport views: **NBA, NFL, NHL, CFB, WNBA, MLB, UFC**. Each has Forecasts, Model Lab, and Data & Sources sections. Browse ranked source-backed matchups, conditional win probabilities, model factors, calibration plots, chronological comparisons, season scores, team statistics, recent results, freshness and missing inputs.

**Daily at 11:17 UTC**, GitHub Actions refreshes public history/schedules, reviews losses and locked challengers, exports current forecasts, and publishes the static dashboard. Main-branch pushes and manual workflow runs also rebuild it. Historical test scores remain sealed. Forecasts expire at verified event start or the conservative date-only cutoff, and are hidden when updates become overdue. [Daily update and privacy details](docs/PAGES.md).

| League | Historical decisive results | Held-out n | Selected specification | Log loss | Brier |
|---|---:|---:|---|---:|---:|
| NBA | 14,208 | 2,676 | logistic, 20-game window | 0.60827 | 0.21058 |
| NFL | 5,776 (plus 15 stored ties) | 1,048 | logistic, 10-game window | 0.63577 | 0.22275 |
| MLB | 7,413 | 1,462 | logistic, 20-game window | 0.68569 | 0.24628 |
| NHL | 2,932 | 441 | logistic, 20-game window | 0.67067 | 0.23889 |
| CFB | 2,021 | 95 | logistic weak w20 | 0.82571 | 0.28724 |
| WNBA | 1,429 | 317 | logistic w10 | 0.58835 | 0.20064 |
| UFC | 2,737 | 284 | elo w20 | 0.67585 | 0.24140 |

These are archived benchmark sample sizes and results, not automatically updated validation claims. Current ingestion counts and daily training hashes are shown on the website. All seven leagues now have daily result/schedule connectors. NBA uses the SportsDataverse mirror of ESPN schedules; WNBA/UFC use the ESPN scoreboard; CFB uses SportsDataverse results and fixtures. Connection status, actual coverage and initial validation are displayed per sport. Sport-specific advanced feature groups were skipped because complete inputs are absent. These limited result-history baselines are not injury-, pitcher- or goalie-aware models. MLB's predictive signal is modest. Probabilities condition on a decisive winner; NFL ties and UFC draws/no contests are excluded. No guarantee, sportsbook value, prop or parlay probability is invented.

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

### Daily feed and model checks

The public dashboard has a compact seven-sport feed overview, team/fighter search, upcoming schedules, recent final results and per-sport model review status. All sports have daily result/schedule connectors; successful connection and actual coverage are shown separately. New sport models are validated only after enough real history is collected. Public APIs provide daily snapshots, not continuous in-game streaming.

Production weights are now guarded: a settled forecast loss triggers a locked challenger, and an independent subsequent backtest must improve log loss without worsening Brier or accuracy before promotion. Fresh result-derived inputs still update daily. Original final-test scores stay sealed. See [promotion policy](docs/METHODS.md#loss-triggered-model-improvement).

[Latest seven-sport backtest review](docs/MODEL_REVIEW.md): 20 challengers per sport, shared chronological folds, richer prior-result features, recency weighting and unchanged independent promotion requirements. Full comparisons are displayed in Model Lab; development gains do not rewrite the archived final test.

The October 22 [quality review](docs/MODEL_REVIEW.md) tests 40 team-sport / 32 UFC candidates, including chronological calibration, fixed Elo blends and scoring profiles. The UFC calibration candidate reduced development probability error at unchanged accuracy; team-sport selections were retained. Independent promotion requirements still apply.
