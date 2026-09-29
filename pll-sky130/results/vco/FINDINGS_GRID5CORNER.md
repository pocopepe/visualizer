# Full 5-Corner Grid — Correction to Review 1's Spot-Check

Review 1 only spot-checked ss/tt/ff (3 of 5 corners) at 3 temperatures, reporting a >3× tempco spread (332-1070 ppm/°C). Full grid now run: all 5 sky130 corners (tt/ff/ss/**sf/fs**) × the complete Vctrl sweep (8 points) and temperature sweep (6 points). Reproduce: `python3 scripts/compile_vco_results.py results/vco/grid5corner results/vco/grid5corner.csv`.

## The spread is much worse than Review 1 reported

| Corner | f(0.9V, 27°C) | K_VCO @ 0.9V | Span (-40→85°C) | Avg tempco |
|---|---|---|---|---|
| ss | 178.0 MHz | 568.2 MHz/V | +13.37% | +1070 ppm/°C |
| **sf** | 246.2 MHz | 580.2 MHz/V | **+1.40%** | **+112 ppm/°C** |
| tt | 226.2 MHz | 669.3 MHz/V | +8.51% | +681 ppm/°C |
| **fs** | 183.7 MHz | 688.7 MHz/V | **+17.49%** | **+1399 ppm/°C** |
| ff | 279.2 MHz | 763.6 MHz/V | +4.15% | +332 ppm/°C |

**Real spread: 112 to 1399 ppm/°C — a 12.5× range, not the 3.4-3.2× previously reported.** The worst corner (fs — fast NMOS, slow PMOS) wasn't in Review 1's spot-check at all. The flattest corner (sf) also wasn't checked and would have looked like good news if it had been mistaken for representative.

K_VCO also varies meaningfully by corner: 568 MHz/V (ss) to 764 MHz/V (ff), a 1.34× spread — smaller than the tempco spread but not negligible for loop-filter sizing robustness across corners (Review 1's loop filter was sized against tt only).

## Consequence for the per-corner compensation decision

This strengthens, not just confirms, the Review 1 decision to define the compensation ratio `C` per-corner rather than as a scalar (`STATUS.md`, `PROJECT_CHARTER.md` decision log). A compensation network sized to the previously-known 3.4× spread would still be off by nearly 4× more at the fs corner. The compensation network (`docs/compensation_model.md`) is derived from the tt fit only so far — corner-specific coefficient refinement is the natural next step before claiming the compensation result generalizes.
