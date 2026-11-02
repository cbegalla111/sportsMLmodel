# Player-prop research

Open **Player props** on the public dashboard. Choose NBA, WNBA, MLB, NFL or NHL, search a player, choose a statistic, enter the exact line offered by your platform, and select Over or Under. The comparison table finds players with consistent results at that same custom threshold. Save candidates to the browser-local shortlist; remove them individually.

This release collects real, completed ESPN public box scores automatically during the existing six-hour Pages job. It does **not** collect live bookmaker player lines or prices, place bets, or estimate a parlay win probability. Custom lines are clearly labeled. Live player markets would require a separate licensed feed and server-side credentials; no secret belongs in Pages JavaScript. The Odds API documents player markets, but its documentation is not a source of free live quotes.

## Interpreting the statistics

Last 5/10/20 use the latest available observations **for the chosen player and statistic**. Show hits, non-push denominators, pushes, and actual observation counts independently. Values equal to an integer line are labeled pushes; actual platform settlement rules may differ. DNP, missing statistics and missing games are not filled with zeros. This can produce selection bias, especially in football reception/rushing groups: a missing zero-opportunity appearance is not necessarily present. Always inspect the logs.

A streak counts consecutive hits among collected observations, stopping at a push or miss. Incomplete collection means it is not a certified streak across every actual appearance. Last-20 Wilson 95% intervals illustrate binomial sampling uncertainty. They assume independent observations from a stable probability, which player outcomes need not satisfy; they are not predictive confidence intervals. Ranking many players and thresholds introduces multiple-comparison bias. No selection here has prospective betting validation.

The latest observed team is historical, not a verified active roster. Selected-day fixtures are matched to that team, but do not confirm an active player, starter, minutes, opposing lineup or injury status. Small samples, role changes, opponent strength, rest and postseason context require separate review. Same-player and same-game parlay legs can be strongly correlated. Do not multiply these descriptive rates to estimate a ticket's chance.

## Collection and provenance

Only final, regular/postseason games are parsed when season metadata is supplied. ESPN daily scoreboards are requested for 60 days (WNBA 120); date-range requests were tested and rejected by the source. Each update collects up to 160 previously uncached final box scores per sport, newest first, so older history fills over subsequent updates. At most 30 observations per player are exported, with event IDs, UTC start times and links to source boxes. Source caches retain up to 180 days; recent scoreboard dates are rechecked. Completed box scores are cached; later official statistical corrections are not automatically reimported in this initial version. Collection limits, missing box scores and upstream coverage can prevent complete logs. Offseason sports may have no current fixtures.

Final boxes are merged by event/player identity so multi-category football players and duplicated hockey skater tables do not create duplicate appearances. Basketball threes use made shots, not attempts. Baseball batter strikeouts cannot populate the pitcher-strikeout market. Optional feed failures preserve cached game logs and surface an error. Team winner models, promotion policies and immutable saved predictions are unchanged.

## Online references reviewed

- [swar/nba_api](https://github.com/swar/nba_api): existing NBA statistics API client and endpoint documentation. Reviewed as an example of structured player-stat acquisition; not installed or claimed as the source of this release's data.
- [The Odds API market definitions](https://the-odds-api.com/sports-odds-data/betting-markets.html): player market taxonomy and the distinction between actual bookmaker markets and historical statistics. No live prop feed is configured.
- [Statsmodels proportion intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html): Wilson binomial interval reference. The dashboard computes the standard formula directly.
- ESPN public scoreboard and summary JSON endpoints: each exported observation links to its actual summary source.

These references informed data structure and uncertainty presentation. They do not establish predictive profitability. Baseball Savant's leaderboard was attempted but returned HTTP 403 from this environment; no Statcast-derived advantage is claimed.
