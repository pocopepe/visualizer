# Temperature Compensation Network — First Results

Idealized behavioral model (deliberate staging choice, same pattern as the Review 1 charge pump — see `blocks/vco/tb_comp_template.spice`, coefficients derived in `docs/compensation_model.md`). tt corner, Vctrl nominal 0.9V.

## Deterministic sweep (6 temperature points, -40 to 85°C)

| Arm | Span (max-min) | % of nominal | vs baseline |
|---|---|---|---|
| Baseline (uncompensated) | 19.249 MHz | 8.51% | — |
| 1st-order (analytically derived k1) | 6.869 MHz | 3.04% | 2.80× better |
| 2nd-order, naive analytical k2 | 10.151 MHz | 4.49% | **worse than 1st-order alone** |
| 2nd-order, empirically refined k1/k2 | 2.521 MHz | 1.11% | 7.67× better than baseline, 2.7× better than 1st-order |

## The naive-vs-refined gap is itself a real finding

The analytically-derived quadratic coefficient (small-signal derivation assuming constant K_VCO — see `docs/compensation_model.md`) made the cold-end residual *worse*, not better (235.6 MHz vs 1st-order's 229.1 MHz at -40°C). Cause: the derivation assumes K_VCO is constant across the Vctrl excursion the compensation itself induces, but Review 1 already established K_VCO is measurably nonlinear (669 MHz/V fit-derivative at 0.9V, but the raw tuning curve compresses substantially at higher Vctrl). The correction overshoots where the real K_VCO differs most from the point-estimate used to derive it.

Fix (zero additional simulation — reused the already-measured 1st-order-compensated residual): fit a fresh quadratic directly to the *measured* post-1st-order residual and derive k1/k2 empirically from that, rather than analytically from the raw uncompensated curve. This refined pair (k1=-1.322e-4, k2=2.894e-7) gave the 1.11% result above. **Takeaway: naive small-signal coefficient derivation isn't sufficient once the correction itself becomes large enough to traverse the VCO's own nonlinearity — empirical/iterative refinement is the right methodology, not a one-shot analytical formula.** Worth stating plainly in any writeup rather than presenting only the refined number.

## Monte Carlo (mismatch) — statistical significance

Device mismatch on (`mc_mm_switch=1`), tt corner, drift = f(85°C) − f(−40°C) per trial, arms paired by seed (same mismatch instance through each arm — see `docs/stats_methodology.md`). n=30 seeds for the 1st- vs 2nd-order comparison (the question that needed it); baseline was run on seeds 1-12, which is ample for a difference this large. Reproduce: `python3 scripts/analyze_mc.py` (saved output: `results/mc_summary_n30.txt`).

**Compensation quality is |drift|, and that's what is tested.** The first version of this analysis compared *signed* drift and reported 1st- vs 2nd-order as significant — but 1st-order over-corrects (drift negative) and 2nd-order under-corrects slightly (positive), so the signed difference was mostly the sign flipping. On |drift| at n=12 the difference was not significant (CI [−0.28, 6.03] MHz). Re-run at n=30:

| Arm | n | Mean \|drift\| | 95% CI |
|---|---|---|---|
| Baseline | 12 | 18.93 MHz (8.4% of f₀) | [16.20, 21.65] |
| 1st-order | 30 | 5.86 MHz (2.6%) | [4.62, 7.09] |
| 2nd-order refined | 30 | 3.37 MHz (1.5%) | [2.33, 4.41] |

| Comparison (paired, \|drift\|) | n | Reduction | 95% CI | Paired t | Wilcoxon | Wins |
|---|---|---|---|---|---|---|
| Baseline → 1st-order | 12 | 12.78 MHz | [9.98, 15.57] | significant | significant | 12/12 |
| Baseline → 2nd-order | 12 | 15.65 MHz | [12.65, 18.66] | significant | significant | 12/12 |
| 1st-order → 2nd-order | 30 | 2.48 MHz | [0.81, 4.15] | significant | significant | 23/30 |

**Result:** both compensation stages significantly reduce drift under mismatch, and the curvature-matched 2nd-order network is significantly better than 1st-order (≈42% lower mean |drift|), with both tests agreeing at n=30. Note the 1st→2nd effect is modest next to the mismatch spread (std ≈3.6 MHz) — 7 of 30 mismatch instances still did better with 1st-order.

## Known limitations, stated plainly
- Idealized behavioral compensation (a B-source correction voltage), not yet a transistor-level PTAT/squaring circuit — the natural next step once a design point is chosen.
- Coefficients here are the tt set; per-corner refits and a held-out-temperature check are in `results/comp/FINDINGS_PERCORNER.md`. The ±0.3% spec is met at ff and sf only.
- Monte Carlo is tt-corner only; mismatch at other corners not run.
