# Per-Corner Compensation — Does It Generalize?

Review 2's first compensation pass (`results/comp/FINDINGS.md`) only proved the approach works at tt. Given the 12.5× corner-to-corner tempco spread (`results/vco/FINDINGS_GRID5CORNER.md`), that wasn't sufficient — a compensation network tuned to one corner's drift curve has no guaranteed relationship to another corner's curve. This refits k1 (analytically, per corner) then k2 (empirically refined from each corner's own measured 1st-order residual, same method as tt — zero extra simulation for the refinement step itself) independently for all 5 corners.

## Result: it generalizes, with real corner-to-corner variation in how well

| Corner | Baseline span | 1st-order span | 2nd-order span | C (1st-order) | C (2nd-order) |
|---|---|---|---|---|---|
| tt | 8.51% | 3.05% | 1.12% | 2.79× | 7.57× |
| ff | 4.15% | 1.06% | **0.10%** | 3.91× | **40.28×** |
| ss | 13.37% | 6.37% | 3.32% | 2.10× | 4.02× |
| sf | 1.40% | 0.42% | 0.24% | 3.32× | 5.77× |
| fs | 17.49% | 9.13% | **5.31%** | 1.92× | 3.30× |

**Every corner improves at both compensation stages — the approach genuinely generalizes, not just at tt.** But the compensation ratio `C` varies by more than 12× across corners (3.30× at fs to 40.28× at ff), which is exactly why the charter's decision to define `C` as `C(corner)` rather than a scalar was correct, not just cautious.

## Two things worth flagging honestly

1. **fs — the worst uncompensated corner — is also the hardest to compensate**, even with a per-corner-refit network: 5.31% residual, more than 4× larger than every other corner's 2nd-order residual. The compensation reduces it substantially (17.49%→5.31%, 3.3×) but doesn't bring it to parity with the other corners. This is consistent with the sensitivity finding (`docs/sensitivity_analysis.md`) that N/P mismatch corners are driven by a different, harder-to-cancel mechanism than absolute device speed.
2. **ff's 40× C is partly an artifact of a small denominator** — ff's baseline (4.15%) was already the second-best of the 5 corners, so a small absolute residual (0.10%) produces a large ratio. Don't read "40×" as "ff compensation is 10× better engineered than tt's 7.57×" — read the absolute residuals (ff: 0.10%, tt: 1.12%) as the more meaningful comparison.

## Out-of-sample check: held-out temperatures

The table above is in-sample — each corner's k1/k2 were fit to the same 6 temperatures they're scored on, and a quadratic correction fit to its own data shrinks the residual partly by construction. To test that, each corner's refined network was re-simulated at 4 temperatures never used in any fit (-30, 10, 40, 70°C). Reproduce: `results/comp/holdout/`, summary in `results/comp/holdout_summary.json`.

| Corner | Span, fit temps (6) | Span, all 10 temps | Max \|dev\| from 27°C, held-out | Max \|dev\| from 27°C, fit temps |
|---|---|---|---|---|
| tt | 1.12% | 1.12% | 0.72% | 0.87% |
| ff | 0.10% | 0.11% | 0.05% | 0.07% |
| ss | 3.32% | 3.32% | 1.99% | 2.46% |
| sf | 0.24% | 0.24% | 0.08% | 0.15% |
| fs | 5.31% | 5.31% | 3.09% | 3.83% |

At every corner the held-out points fall inside the envelope of the fitted ones — the fits generalise to unseen temperatures within the range. Scope of that claim: interpolation within -40→85°C (the spec range), not extrapolation beyond it.

## Against our own specification — met at 2 of 5 corners

The Review-1 target was residual free-running drift **< ±0.3%** over -40→85°C, i.e. max deviation from the 27°C value. Using the last column above (all fit temps; held-out points are smaller):

| Corner | Max \|deviation\| | Meets ±0.3%? |
|---|---|---|
| ff | 0.07% | **yes** |
| sf | 0.15% | **yes** |
| tt | 0.87% | no (≈2.9× over) |
| ss | 2.46% | no |
| fs | 3.83% | no |

**The target is met at ff and sf only, not at the typical corner.** State this plainly in any review rather than letting the span table imply otherwise. What closes the gap is Review-3 work: a transistor-level network whose PTAT slope tracks process (so the correction follows the corner instead of being refit per corner), and/or a per-corner trim.

## What this means for the H1 regression

This gives 5 additional (C, corner) data points beyond the original tt-only pair, but they're not directly usable as-is for the ε_res-vs-C regression (`PROJECT_CHARTER.md` §2.1) because each corner's C was computed against that corner's own baseline, not a single common reference — the regression needs C values from a controlled compensation-*strength* sweep at one fixed corner (see `docs/compensation_model.md`'s α sweep, `results/comp/alpha/`), not from varying corners. Keep these as separate, complementary evidence: this table shows compensation *generalizes*; the α sweep is what feeds the H1 statistical test.
