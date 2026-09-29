# Statistical Methodology

From a dedicated research pass (2026-09-29) into how to test these hypotheses properly, not just eyeball single-run numbers. No scipy/numpy in this environment — `scripts/stats.py` hand-rolls exactly what's needed (t-CI, paired t-test, Wilcoxon signed-rank normal approximation, OLS regression with slope CI), all self-checked in `if __name__ == "__main__"`.

## Monte Carlo sample size
No pilot variance available yet at design time. Recommended approach: run a pilot batch (n≈30 typical), compute sample std `s`, then size the real run via `n = (z*s/E)^2` for a target margin of error `E` at 95% (z=1.96). Practical range for analog IC Monte Carlo *mean/CI* characterization (not tail/yield estimation, which needs far more) is commonly n=100-500. **What we ran:** a first pass at n=12, then n=30 for the 1st- vs 2nd-order comparison once n=12 proved underpowered for it (see below). Baseline vs compensated needed only n=12 — the effect is several times the spread.

## Paired comparison (compensation arm A vs B)
Use **paired** tests — same mismatch seed run through both arms, which is strictly more powerful than unpaired and is what fixed SPICE seeds buy for free. Paired t-test if the *differences* are approximately normal (check the differences, not the raw values); Wilcoxon signed-rank as a corroborating check regardless (safe down to ~n=6, cheap to run alongside). If both agree, that's stronger than either alone.

## Test the quantity that means "better" — a mistake we made and caught
The first Monte Carlo analysis compared compensation arms on *signed* drift f(85°C)−f(−40°C) and reported 1st-order vs 2nd-order as significant. It wasn't meaningful: 1st-order over-corrects (drift ≈ −6 MHz) and 2nd-order lands slightly positive (≈ +3 MHz), so the signed difference is large mostly because the sign flipped. Compensation quality is |drift|. Re-tested on |drift| at n=12, the 1st-vs-2nd difference was not significant (CI [−0.28, 6.03] MHz). Re-run at n=30 it is: reduction 2.48 MHz, CI [0.81, 4.15], both tests agree, 23/30 seeds. `scripts/analyze_mc.py` now tests |drift| only and prints a win count per seed. General rule: before running a test, write down which direction of the metric is "better" — if both a large positive and a large negative value are bad, test the magnitude.

## H1 regression (ε_res vs compensation ratio C)
OLS slope with 95% CI (t-dist, df=n-2) and R². Pre-register the null *before* looking at data: β=0 (no scaling relationship) vs β=1 (proportional 1:1) — decide which is being tested, don't pick after the fact. **Point count: 3-4 (C, ε) points is not enough** — df=1-2 gives a CI too wide to falsify anything. Target 6-10 distinct C values minimum (general regression-literature guidance: N≈8 workable only for low-scatter data, N≈25 with real scatter — lean toward the higher end once cross-flow ε data exists).

## Novelty verification note
This methodology research pass also verified (separately, see `PROJECT_CHARTER.md` §3.4) that "linear + quadratic temperature compensation for oscillators" is patented generically (US 9,748,962 B2, Infineon, 2017) — reframed our second-order compensation claim to the narrower, still-open composite: ring-VCO + closed-loop PLL + open PDK + statistically-validated quantification.
