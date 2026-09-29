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

n=12 seeds (device mismatch, `mc_mm_switch=1`), paired across baseline/1st-order/2nd-order-refined arms (same seed set, so paired tests are the correct tool — see `docs/stats_methodology.md`), tt corner, drift metric = f(85°C) - f(-40°C) per trial. Below is a first pass, explicitly under the recommended pilot size (n≥30) — reported honestly as directional, not final.

<!-- MC_RESULTS_PLACEHOLDER -->

## Known limitations, stated plainly
- Idealized behavioral compensation (a B-source correction voltage), not yet a transistor-level PTAT/squaring circuit — the natural next step once a design point is chosen.
- Coefficients derived/refined against the **tt corner only**. Given the 12.5× corner-to-corner tempco spread (`results/vco/FINDINGS_GRID5CORNER.md`), this compensation will very likely underperform or overcorrect at ss/sf/fs/ff — per-corner refinement is required before claiming general validity, not optional polish.
- n=12 Monte Carlo trials is a first pass, below the recommended pilot size of n≈30 (`docs/stats_methodology.md`) — re-run before this goes in a final report.
