# Result and pregame-feature schema

UTF-8 CSV, one row per completed event. All seven league codes are supported: NBA, NFL, NHL, CFB, WNBA, MLB, UFC. No demo data is loaded. Synthetic test fixtures exist only inside tests.

Required columns:

| Column | Meaning |
|---|---|
| event_id | Globally unique stable ID; prefix with source and league |
| league | One of the seven exact codes |
| date | YYYY-MM-DD UTC event date; historical results cannot be future dated |
| home / away | Distinct source-canonical opponents; for UFC, first/second fighter |
| home_score / away_score | Finite nonnegative final scores including OT/shootout; UFC can use 0/0 with an explicit decision outcome |
| outcome | home, away, draw, no_contest |
| source | Required provenance, preferably URL, retrieval date and source version |
| neutral | 1 for neutral venue; 0 otherwise |

NFL/CFB ties and UFC draws/no contests are stored, but excluded from binary training. UFC decisive outcomes may have zero scores because judging is not a points differential. Do not interpret UFC score-margin features as validated: no UFC model has been trained. NBA/WNBA/NHL/MLB must use final eventual-winner results, not regulation ties. Betting settlement rules are not modeled. Idempotent reimports do not create duplicates. Conflicting revisions to an existing ID are rejected for review; history is not silently overwritten.

Optional numeric paired columns use home_ and away_ prefixes. See `sportslab/data.py:FEATURES` for the exact per-sport allowlist. Each row with extra features requires `feature_asof`, a timezone-aware ISO timestamp converted to UTC and strictly before its UTC event date. This conservative date boundary excludes same-day updates to avoid unknown event start times. Timestamp assertions and source permission remain the uploader's responsibility. Units and feature definitions must be consistent across the full dataset. The current benchmark uses only result-based history: these advanced feature groups were skipped, not invented or validated.

Odds, spreads, supplied Elo ratings, market probabilities, unsupported columns, missing required fields, nonfinite inputs and inconsistent outcomes are rejected. Core-model arrays are built from an explicit feature list, never all numeric columns. Downloaded NFL raw archives contain upstream market columns but are isolated source evidence; the adapter discards them before ingestion. They never reach features, model selection, or predictions.

Daily feature construction reads every game's inputs before updating any result on the same date. Rating state, trailing wins/margin and rest use strictly earlier dates. At least five prior appearances per opponent are required. Games with insufficient history are excluded from evaluation and forecasts, rather than filled with invented statistics.
