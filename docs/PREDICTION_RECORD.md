# Prediction grading and future schedules

## Correct / incorrect / unresolved

The seven-calendar-day overview now counts one saved prediction per event. It prefers the current prediction policy's eligible pregame pick, otherwise the earliest eligible saved version. If all versions are invalid, the event stays explicitly unscored. It never chooses the version that happened to be right. The full original-policy audit remains expandable, and saved probabilities and publication times stay unchanged.

The overview separates:

- **Correct / Incorrect**: a verified decisive final and an eligible pregame prediction.
- **Pending / in progress**: a started game still awaiting its final, with a known start/recent window or source-confirmed in-progress status.
- **Awaiting source result**: an older or time-unverified event whose final cannot be confirmed. Age alone never implies a winner or a loss.
- **Unscored**: draws/no contests, confirmed cancellations/postponements, or predictions whose publication occurred after a corrected official start.

Scheduled future games belong in the upcoming schedule and are not counted as unfinished past predictions. Accuracy is correct divided by correct plus incorrect; all unresolved/unscored categories stay outside that denominator.

## Stable event identity fixes timezone mismatches

Shared result matching now uses a canonical provider event ID and validated opponents before calendar dates. This handles a game saved on its local date but reported on the following UTC date. A known provider ID cannot fall back to a different same-team/same-day game, protecting baseball doubleheaders. Explicit NHL team aliases and neutral UFC orientation changes are handled. Conflicting results for one event do not silently produce a grade.

The hourly job checks recent unresolved saved events using ESPN summaries, the official MLB game feed, the official NHL game endpoint and ESPN UFC cards. Exact identity, opponents, completed status and finite scores are required. Primary NFL results continue to use the existing nflverse result feed. Verified finals are cached separately for grading; they do not overwrite the model's immutable training dataset. Old verified cached finals survive a temporary source failure. Finals resolved by this secondary check are rechecked daily; unresolved recent events are retried hourly. Already-settled primary-feed results retain their original source path. Missing, removed or inaccessible events remain explicitly unresolved, rather than inventing a cancellation or winner.

The exporter, live loss ledger and injury-outcome recording use the corrected outcome evidence. Corrected official start times can expose a forecast or injury observation recorded too late. Such entries are excluded from grading/training; known-invalid entries originally made after their own stored start are not introduced into public history. First-observed pregame records are not rebuilt from a result.

Real checks during development verified the previously unresolved Atlanta Hawks–Cleveland Cavaliers event `401909893` (114–111) and Atlanta Dream–Golden State Valkyries event `401918310` (80–69). Their source dates differed from saved dates. Other missing finals were not guessed. Result reconciliation is for accurate accounting, not a claim that model forecasts improved.

## Published future games

The previous 14-day fixture collection cap was expanded to a rolling **365-day calendar**, as far as each provider has published actual fixtures. NBA uses the published season schedule; NFL uses all available schedule rows; MLB requests across the calendar-year boundary; NHL merges full club-season schedules with its near-date feed; CFB and WNBA attempt optional next-season schedules; UFC requests published future cards/bouts. Unknown opponents, unpublished seasons, unannounced fight cards and uncertain dates are not fabricated. If NHL's full-season request is unavailable, verified near-date fixtures remain available with an explicit broader-coverage note.

Exhibitions can appear in schedules without entering validated regular/postseason model training or receiving forecasts. Explicit conditional MLB games remain schedule-only. The calendar's **Published game dates** selector and **Next games** button make later fixtures accessible. An expandable all-upcoming table pages through verified fixtures, with a Show all option. The inspected real NBA feed contained 1,093 future fixtures through April 12, 2027 (source UTC dates).

The model forecast window remains 14 days with existing freshness/validation guards. Distant schedules do not create probability forecasts or player-prop suggestions from today's roster information. Snapshot assets have content fingerprints so updated record controls load without a manual browser-cache reset.
