# Player stat builder

Open Players → Stat builder, or choose **Adjust with slider** on a daily target. Moving the slider updates the threshold, observed hits/misses, historical hit rate, streak, game-value chart and Wilson interval immediately. Keyboard arrow controls and manual numeric entry are supported. Targets stay positive. The default comparison is **at least**, including equality; platform over/under modes keep exact-line pushes separate.

Use the last 5, 10 or 20 collected observations. The 80%, 90% and 100% historical presets select the highest observed target reached in the required share of that full window. If the window is incomplete or the only qualifying target is zero/negative, the preset explains why it cannot offer a target. It never invents a positive threshold. Selecting a different stat/player refreshes the slider range and starting target.

Game-linked research uses only logs dated before the selected game's start, even if that game has already finished. General research excludes future observations and deduplicates game IDs. Shortlisted builder targets save their hit count, graded sample, window, collection timestamp and linked event, so a later data update cannot silently change the saved supporting record. Shortlists remain local to the browser.

A historical 90% rate is not a calibrated 90% chance of reaching that number in the next game. Wilson intervals describe binomial sampling uncertainty, under assumptions that repeated appearances may not satisfy. Searching many players and thresholds creates selection bias. Neither multiplying historical hit rates nor combining correlated legs gives a validated parlay probability. Player availability, role, minutes, opposition and current roster still require review.

## Online methods reviewed

- [NIST: confidence intervals for proportions](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm): Wilson score interval and limitations of simpler normal approximations.
- [statsmodels: proportion confidence intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html): Wilson implementation/reference and alternative interval methods.
- [NumPy: empirical quantile definitions](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html): discrete empirical quantiles. The target uses an explicit order statistic with a ceiling hit-count requirement, including equality, rather than interpolating an unsupported guarantee.

These sources inform the statistics display; they do not establish a validated betting edge.
