# Outcome learning and NBA review

Every sport uses causal adaptive research features: NBA, WNBA, NFL, CFB, MLB, NHL and UFC. Team/fighter strength updates use outcome minus its pregame adaptive estimate. An unexpected win and the opponent's unexpected loss generate opposite signed updates; larger surprises produce larger residuals. Both correct and incorrect outcomes contribute. UFC result encodings are never treated as scoring margins.

At each hourly publication, verified settled predictions also receive an outcome-learning audit based on the original saved probability. The dashboard shows correct/incorrect totals and the biggest unexpected outcomes. Unscored, canceled and post-start entries are excluded. Saved probabilities stay immutable.

A newly settled correct result can now open an eligible adaptive challenger trial, in addition to a loss. The specification must already qualify in chronological development backtests. An active trial remains frozen so its future evaluation stays independent. Production promotion still requires the existing minimum sample, calendar coverage, accuracy, log-loss, Brier and paired uncertainty checks. This does not mean every result changes live weights.

## NBA schedule/form research

The added candidate view combines existing uncertainty and outcome-feedback signals with shrunk short/long scoring margins, recent margin trend, venue performance, back-to-backs, three games in four days and four games in six days. Scoring form expires after 120 days; margins are capped at 30 points. Inputs for every date are calculated before any outcomes from that date. Rest effects are learned, not assigned a fixed penalty.

Twelve fixed schedule/form specifications were added to the existing 24-candidate NBA context review. Selection excludes July 2025 onward. The selected development candidate improved accuracy from 66.544% to 67.058% on 2,726 development predictions, while reducing log loss from 0.612553 to 0.611972. On the separate, previously used 2025–26 historical confirmation cohort, accuracy fell from 68.381% to 67.927% on 1,322 games; log loss and Brier also worsened. It therefore does **not** qualify for a live trial. This is research evidence, not a claim of improved production accuracy. Full evidence: `artifacts/research/nba-context-v2.json`.

## Dashboard organization

Games contains Forecasts and Prediction record. Players contains Find props and Player game logs. Research contains Models & accuracy and Data & injuries. Every section has a short purpose description. Models starts with the active model and outcome-learning audit, followed by historical evaluation; experiments, injury learning and promotion evidence are expandable separately.
