# Courtside · private Sports ML Lab

A working password-protected research dashboard for statistics-only conditional moneyline probabilities. All seven requested sports are selectable: **NBA, NFL, NHL, CFB, WNBA, MLB and UFC**. Readiness is explicit; missing leagues do not receive invented predictions.

## What works

- SQLite-persisted real result imports, settings and prediction history; CSV/manual entry with immutable event IDs and validation.
- NBA and NFL chronological baseline comparisons: Elo, regularized logistic regression and small boosted trees. No sportsbook inputs; transparent leakage-resistant date grouping and shifted history.
- Final held-out log loss, Brier, accuracy, AUC, calibration plots/bands, season reports, baseline comparisons and approximate block-bootstrap performance intervals.
- Matchup selection and scenario labeling, limited live NFL forecasts with fresh result history, provenance, stale-data withholding, and source-backed upcoming NFL fixtures.
- Six-hour feed updater, source archives/hashes, CSV inbox, frozen-specification weight refresh, daily local backups and verified restoration.
- Random-password login, hashed credentials, authenticated APIs, CSRF protection, cookie controls and loopback-only defaults.

## Actual initial data and held-out results

| League | Real decisive results | Final test n | Selected specification | Log loss | Brier |
|---|---:|---:|---|---:|---:|
| NBA | 14,208 | 2,676 | logistic, 20-game window | 0.60827 | 0.21058 |
| NFL | 5,776 (plus 15 stored ties) | 1,048 | logistic, 10-game window | 0.63577 | 0.22275 |

NBA archive: November 2004–June 2015; **current NBA forecasts are withheld**. NFL import: September 2005–October 19, 2026. These are limited result-only historical benchmarks, not validated injury-aware, pitcher-aware or fighter-specific models. NFL output is conditional on no tie; it does not price ties or bookmaker settlement. Advanced-feature ablation is recorded as skipped because inputs are absent.

NHL/CFB/WNBA/MLB/UFC have schemas and entry workflows but **no validated models or loaded historical dataset**. NBA current/CDN, MLB and NHL connectors currently encounter cloud network denials and are unverified. CFB/WNBA/UFC require permitted CSV data or a future verified feed. Auto updates do not provide missing inputs or keep a sleeping/unpublished environment running. No live odds, player props or parlays are populated.

## Start

```bash
cd /workspace/sportsMLmodel
bash scripts/install.sh
bash scripts/start.sh
```

Retrieve your generated password privately from `/workspace/.sportsml-private/initial-password.txt`. Never commit it. The website runs locally on port 8765; **no privately hosted URL exists yet**. GitHub is durable source storage, not a Python hosting service.

- [Setup, automatic refresh, backup, recovery and private hosting](docs/OPERATIONS.md)
- [Data schema and outcome rules](docs/DATA_SCHEMA.md)
- [Primary sources, model selection and limitations](docs/METHODS.md)
- [Validation evidence](docs/VALIDATION.md)

Actual reports, held-out forecasts and selected model weights are under artifacts/. Runtime databases, raw archives and authentication are outside the repository. Push source commits and keep an off-machine private backup; a local commit or local backup alone does not protect against workspace loss.
