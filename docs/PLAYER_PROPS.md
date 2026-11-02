# Player-prop research

Open **Player props** on the public dashboard. Choose NBA, WNBA, MLB, NFL or NHL, search a player, choose a statistic, enter the exact line offered by your platform, and select Over or Under. The comparison table finds players with consistent results at that same custom threshold. Save candidates to the browser-local shortlist; remove them individually.

This release collects real, completed ESPN public box scores automatically during the existing hourly Pages job. It does **not** collect live bookmaker player lines or prices, place bets, or estimate a parlay win probability. Custom lines are clearly labeled. Live player markets would require a separate licensed feed and server-side credentials; no secret belongs in Pages JavaScript. The Odds API documents player markets, but its documentation is not a source of free live quotes.

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

## Automatic Prop Finder

**Prop Finder** is a separate top-level tab. Select the event date with the dashboard date controls, select a sport and upcoming game, then set the number of suggestions or **Show all available**. The finder scans players whose latest observed team matches either opponent. It supports Over, Under or Both; a specific statistic; an adjustable 60–90% minimum consistency estimate; and a 5/10/15/20-observation minimum. Five is the initial minimum to accommodate early-season and weekly sports; results below ten observations are explicitly labeled small samples.

Thresholds are a fixed catalog of alternate research lines in `web/prop-finder.js`, not real bookmaker offers. For each player/statistic/direction, choose the most demanding catalog threshold meeting both the smoothed last-20 estimate and the raw last-five minimum. The estimate is `(hits + 2) / (n + 4)`, an illustrative Beta(2,2) shrinkage toward 50%. Ranking uses the Wilson lower bound on the raw hit proportion, then estimate and sample size. Keep at most one candidate per player/statistic, avoiding repeated nested thresholds for the same statistic. Different statistics on the same player can still be correlated.

Only observations before both now and the fixture start can be used. The game must be upcoming, the public schedule and collection must be fresh, and the player's latest collected appearance must be within 30 days. Both teams' players are considered. Last-observed team matching does not verify active rosters, injuries, starters or expected minutes. Missing games/zero-opportunity observations can bias the estimates. Lines and players are selected on the same historical sample: these estimates are **not independently validated game-specific probabilities**, and scanning many options introduces selection bias. The actual opponent is used to identify the fixture and eligible historical teams, not to claim an opponent-adjusted predictive model.

The count is a display limit, not a promise to find that many qualifying candidates. Show all returns the finite qualifying set; requesting more never generates duplicate or unsupported candidates. Shortlists no longer have the previous 20-item cap. They remain browser-local and subject to browser storage limits. Each candidate includes hit counts, recent hits, observed streak, uncertainty lower bound, last appearance, source link and inspectable results. The ordinary **Player props** tab remains available for exact custom-line research.
