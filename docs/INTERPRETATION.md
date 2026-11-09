# Reading the model explanations and daily board

The daily board shows source-reported game status/scores, the original saved pregame probabilities and verified correct/incorrect grades. If no pregame probability was saved, the game still appears without an invented forecast. Unresolved grades remain pending even when a source score is displayed. The record summary is **all-time recorded picks**, not a fabricated season record. Source-provided team logos use an allowlisted ESPN image host and fall back to monograms. Market odds and disagreement markers are omitted because no verified odds feed is configured.

The “Why this pick” dialog opens the current explanation for upcoming games, explicitly distinguishing it from the first saved probability on the board. Historical games show only explanations actually captured at publication; missing older explanations are never reconstructed with later data. The model, prop builder, full history and research views remain available.

## Ranked probability effects

For a supported standardized logistic model, each input has:

- A readable name and description.
- The actual input and its reference value (the training average).
- Which team that input favors and its probability-point effect.
- The home-win probability if only that input were reset to the reference.

For example, if home probability is 63% and resetting one input gives 57%, that input adds **6 percentage points toward home** while other inputs stay fixed. This is not a six-percent relative change.

Standardized linear contributions are `(input − training mean) × coefficient / training scale`. Their sum plus the intercept exactly reconstructs fitted log odds. The reference probability is the sigmoid of the intercept, including typical conditions learned by the model. A constant home-venue feature can have zero fitted contribution because the typical home effect is already absorbed into the intercept.

**Probability-point effects do not add together.** The sigmoid is nonlinear, and variables can be correlated. These are descriptions of the fitted model, not proof that rest, scoring margin or another factor causes the game result. Team-rating and win-rate differences are not the individual teams' raw statistics. Sport-adjusted recovery is bounded; long layoffs are not assigned unlimited benefits. Injury reports remain separate because no numerical injury adjustment has passed validation.

The fixed Elo model receives an exact rating/home-venue breakdown referenced to equal ratings at a neutral venue. The known rest-guard wrapper is explained using its active columns, excluding the legacy metadata column. Every explanation is checked against the actual prediction; unsupported wrappers, nonlinear models or mismatches return an explicit unavailable status instead of invented importance. The implementation uses direct fitted-model arithmetic, avoiding repeated model calls per variable. Technical log-odds/raw inputs remain expandable.

The top three effects are saved with newly recorded picks so historical explanations remain attached to the original probability. Previously saved picks and metrics are not rewritten.

## Latest optimization check

Using the verified public snapshot from November 9, 2026 at 17:30 UTC: NBA 91/138 correct (65.94%); NFL 28/42 (66.67%); NHL 82/131 (62.60%). On the later chronological NBA check, the tested calibration changed 41/54 correct to 40/54 and worsened probability scores. On NHL it slightly improved log loss/Brier but changed 32/51 correct to 31/51. Both are rejected under the non-worse-accuracy requirement. NFL still has too few distinct saved game dates for that study. Existing model weights are preserved; no live accuracy gain is claimed. Evidence is in `artifacts/research/priority-saved-predictions.json`.
