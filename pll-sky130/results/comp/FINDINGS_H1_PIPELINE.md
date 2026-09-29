# H1 Regression Pipeline — Validated, Not Yet the Real Test

`PROJECT_CHARTER.md` §2.1 hypothesis H1 needs ≥6-10 distinct (C, ε) points for a defensible regression (per `docs/stats_methodology.md`). Review 1 had exactly 2 (1st-order, 2nd-order). This extends the compensation-strength sweep (`docs/compensation_model.md`) to generate enough **C** values and proves the regression machinery works correctly — the actual H1 test still needs **ε** (ngspice-vs-Spectre disagreement), which is blocked on Virtuoso access.

## What was run

tt corner, α ∈ {0, 0.25, 0.5, 0.75, 1.0, 1.25} scaling both compensation coefficients (`k1=α·k1_full`, `k2=α·k2_full`), 6 temperature points each. C computed as baseline-span / compensated-span at each α.

| α | Span | C |
|---|---|---|
| 0 (baseline) | 8.51% | 1.00× |
| 0.25 | 6.66% | 1.28× |
| 0.5 | 4.81% | 1.77× |
| 0.75 | 2.96% | 2.87× |
| 1.0 | 1.12% | 7.57× |
| 1.25 | 0.71% | 12.04× |

**OLS regression (C vs α):** slope=8.59, 95% CI=[2.93, 14.26] (excludes both 0 and 1), R²=0.82, n=6, df=4.

## Two things worth flagging honestly

1. **This is a pipeline validation, not the H1 test.** H1 is about ε_res vs C (cross-flow simulator disagreement vs compensation ratio), not α vs C (an internal relationship within ngspice alone). What this proves: (a) the α-sweep produces a well-behaved, monotonic range of C values suitable for a real regression once ε data exists, (b) the stats.py regression code runs correctly on real data (CI, R², excludes-zero/-one all computed correctly), (c) C is clearly *not* linear in α (R²=0.82 on a relationship that's visibly convex/accelerating, not noisy-linear) — worth remembering when the real H1 regression is run: don't assume a linear ε-vs-C functional form without checking it, the same way this one turned out not to be linear in α.
2. **C keeps increasing past α=1.0** (7.57× → 12.04× at α=1.25), meaning the tt "full-strength" empirical refit (§ `results/comp/FINDINGS.md`) wasn't actually the optimum — slightly over-driving the correction did better. Not chased further here (time-boxed), but worth noting for anyone tuning this network further: the empirical-refit method converges toward a good point, not necessarily the exact optimum in one iteration.

## Status
Ready for the real H1 regression the moment ε (Spectre cross-validation) data exists — swap the x-axis from α to measured ε_raw/ε_res pairs, same `stats.ols_regression` call, no new tooling needed.
