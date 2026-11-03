# NBA development and injury recording

## Are injuries being recorded?

Yes. The hourly job collects timestamped NBA injury listings and preserves source payloads with hashes. New payload archives are gzip-compressed to keep hourly retention practical; existing JSON archives remain valid. A first-observed snapshot is saved before each eligible game, within 24 hours of its source-verified start. Outcomes settle later. The dashboard's NBA Model lab shows archived report count, saved/pending/settled observations, current training schema, and recent capture/start timestamps. Missing counters in an older static snapshot mean they have not been exported yet, not that no records exist.

NBA injury learning now records more than headcounts:

- Player identity, reported status, team and reporting timestamp at capture.
- Up to ten prior observed appearances in the previous 30 days, for the same team and strictly before capture; future games and other-team games are excluded.
- Mean points, rebounds and assists represented by reported absences; uncertain-status scoring is separate.
- Unknown-production flags and sample counts. Missing history is not a claim that a player has no value.

Those are recent-production proxies, **not projected point deductions**. They do not establish starter status, replacement quality, minutes or causal player value. Long-standing absences may already be reflected in team form. Source collection must precede capture and be recent; historical injury records are never invented from a later report.

First saved observations remain immutable. Existing count-only records are preserved and not retrospectively filled using today's player information. New player-aware NBA records use `nba-production-v2`; the first chronological comparison requires 200 settled records in that schema. The dashboard separately reports all settled games and the eligible current-schema cohort, so preserved older records are not confused with missing data. Ledger writes are atomic. An unreadable existing ledger is preserved and marked for recovery instead of silently reset.

**Current winner percentages are still result-history baselines.** Reported absences and uncertain statuses filter automatic props and flag team matchups. No numerical injury adjustment is approved before validation. The research recorder can learn from later results; it cannot manufacture the earlier, timestamped injury history needed to train immediately.

## Focused NBA model study

Added an NBA feature family describing season maturity, the combined uncertainty of both teams, rolling global surprise/probability loss, and regularized interactions with strength, margin and home setting. Existing difference-only uncertainty can miss cases where both teams are uncertain, so the new study explicitly tests their sum. Every same-date input precedes all same-date outcomes. Fixed rolling rates and season resets are research specifications, not clinical assumptions.

The 24-candidate catalog contains 12 regularized contextual models, three chronological temperature-calibrated contextual models, three soft blends preserving the retained feedback feature view, and six calibration/refit alternatives applied directly to the retained feedback specification. Training/calibration dates are separate; outer development validation remains unseen. Candidate selection uses only 2022–June 2025. The 2025–26 historical follow-up has already been reused by earlier research and is not fresh independent evidence.

The development-selected constrained decision-calibration candidate gained two correct picks over 2,726 development games: **66.5444% → 66.6178%**; log loss **.612553 → .612284**; Brier **.212048 → .211923**. But on the identical 1,322 historical follow-up games it fell from **904 correct (68.3812%) to 888 (67.1710%)**, with worse log loss (.603939 → .605853) and Brier (.207853 → .208904). It was **rejected**. The retained modern feedback candidate and live champion were not overwritten. This study does not establish a live NBA accuracy gain or a new 70% result.

Hourly builds cache the fixed study by development data/catalog/reference fingerprint. A future NBA-focused candidate can enter the existing adaptive shadow lane only if development and historical checks pass; live replacement still needs 100 new results over eight calendar weeks and the paired probability/accuracy improvement gate. Existing trials are preserved.

## Hourly runner repair

A real follow-up run exposed an inference allowlist omission from the prior adaptive release: `context_feedback` could be researched and locked but was rejected by `model_features` when the next hourly run evaluated the challenger. The allowlist now includes both that supported feature family and the new NBA context family. Regression tests serialize an adaptive challenger and evaluate it through actual production inference; model-building-only or mocked-trial tests did not cover that path. Experimental box-score variants remain excluded from production inference until their source/lineage integration is validated.

Full study specifications, folds and metrics: `artifacts/research/nba-context-v1.json`. This development extends the temporal validation and calibration methods documented in [continuous learning](CONTINUOUS_LEARNING.md).
