# Injuries, explanations and actual prediction results

## What affects the dashboard now

The six-hour public update collects ESPN injury listings for NBA, WNBA, NFL, MLB, NHL and CFB. Each report carries its source timestamp, observed timestamp, player identity, reported status, position, team and source URL. Source timestamps must be within eight hours; malformed/future records and entries older than 180 days are rejected. Missing names never imply a healthy or starting player. Reported team mismatches are flagged rather than reassigned silently.

Prop Finder requires a fresh valid injury feed. Reported out/injured-reserve/injured-list/inactive/suspended players are excluded. Doubtful, day-to-day, questionable, probable and unknown statuses are treated as uncertain and excluded too. A listed Active player or a player absent from the injury list can qualify statistically, but is not a confirmed starter; role, minutes and active roster still require checking. An absent injury name is not proof of availability. Historical custom-line research remains viewable with an availability notice.

Five live sources were verified from this environment. The college-football endpoint returned only 2020–2021 records despite a current response timestamp, so those records were rejected. UFC injury coverage is not configured. Source failure retains the previous report for audit but marks coverage unavailable; retained data cannot clear a player for automatic suggestions. Injury reports apply to current observed listings, not verified future game lineups.

Team predictions now carry `injury_context`, flag affected matchups for injury review, and display both teams' reported players and dates. **The numeric winner probability remains the existing result-history baseline.** No arbitrary penalty, fixed point value or assumption about replacements is applied. This release does not claim that existing models learned injury effects or improved their accuracy.

## Learning injury effects without future information

Archive each verified source response with its observation time and SHA-256 outside the public website. For each forecast first observed within 24 hours before a verified start, freeze the baseline probability/model lineage, first observed injury features, source-check time and observation time. Date-only events cannot become training observations. Later reports cannot overwrite the frozen first observation. Only matched final outcomes settle those observations after the event starts.

Features are baseline log odds plus away-minus-home counts of reported absences and uncertain statuses, absent quarterbacks in NFL/CFB, and absent goalies in NHL. Basketball guards do not count as goalies. These are reported position counts, not claims about who would start or how valuable a player is. The absence of starter, player-value and replacement-quality features limits the potential model.

After at least 200 settled observations **per league**, run a fixed regularized logistic research comparison on earlier dates, with the latest 25% of dates for chronological validation (at least 100 train and 50 validation observations). Compare identical games to their actually saved baseline probabilities using log loss, Brier score and winner accuracy. The historical research gate requires log-loss gain of at least .002 and non-worse Brier/accuracy. This is research evidence, not final independent validation. It never overwrites a champion or saves invented historical injury states.

There is no automatic production promotion for this injury calibration yet. Existing champion promotion and first-published prediction policies remain unchanged. Passing a historical comparison cannot bypass the required separate prospective checks; numeric injury adjustments require validated data and an additional reviewed promotion integration. Until then, team probabilities stay explicitly labeled baselines. Collection and fixed research comparisons occur automatically with updates.

## Why a team is favored

Select a forecast to see **Why [team]?**: both probabilities, the strongest available fitted log-odds contributions supporting the favorite, a recent-results comparison, and injury listings. For models without reliable contribution output, the dashboard says so instead of inventing individual factor importance. Recent context is descriptive, not a causal explanation. Reported injuries are displayed alongside the model evidence, not described as already included in baseline weights.

## Right / wrong

The forecast view includes correct, incorrect, pending, and observed accuracy for seven calendar days including today. **Right / wrong** opens the actual saved pregame record and final results. Accuracy is correct winner picks divided by graded picks; unresolved or non-decisive outcomes do not inflate the denominator. Distinct saved prediction policies can have separate picks for one event and are disclosed separately. No prior prediction is reconstructed from a known result. Results settle after refresh, so games in progress or not yet imported remain pending.
