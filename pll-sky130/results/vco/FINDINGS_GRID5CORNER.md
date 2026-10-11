# Full 5-Corner Grid — Correction to Review 1's Spot-Check

Review 1 only spot-checked ss/tt/ff (3 of 5 corners) at 3 temperatures, reporting a >3× tempco spread (332-1070 ppm/°C). Full grid now run: all 5 sky130 corners (tt/ff/ss/**sf/fs**) × the complete Vctrl sweep (8 points) and temperature sweep (6 points). Reproduce: `python3 scripts/compile_vco_results.py results/vco/grid5corner results/vco/grid5corner.csv`.

**Corner definitions (sky130B, volare c6d73a35), corrected 2026-10-11.** `sf` = NMOS **fast** / PMOS **slow** (NMOS Vth0 -27 mV, mobility +5%). `fs` = NMOS **slow** / PMOS **fast** (+27 mV, -5%). ss/ff shift NMOS Vth by only +/-15 mV, so the skew corners are *more* extreme on NMOS than ss/ff. An earlier version of this repo had sf/fs labelled backwards. Single-device check (W/L 2/0.5, |Vgs| = 0.9 V, 27 °C), NMOS Id: sf 45.1, ff 42.8, tt 36.2, ss 30.3, fs 28.2 µA.

## The spread is much worse than Review 1 reported

| Corner | f(0.9V, 27°C) | K_VCO @ 0.9V (local, corrected) | Span (-40→85°C) | Avg tempco |
|---|---|---|---|---|
| ss | 178.0 MHz | 815 (~820) MHz/V | +13.37% | +1070 ppm/°C |
| **sf** (fast-N / slow-P) | 246.2 MHz | 582 (~580) MHz/V | **+1.40%** | **+112 ppm/°C** |
| tt | 226.2 MHz | 887 (~890) MHz/V | +8.51% | +681 ppm/°C |
| **fs** (slow-N / fast-P) | 183.7 MHz | 1018 (~1020) MHz/V | **+17.49%** | **+1399 ppm/°C** |
| ff | 279.2 MHz | 936 (~940) MHz/V | +4.15% | +332 ppm/°C |

*K_VCO column corrected 2026-10-11.* The values originally tabulated here (ss 568.2, sf 580.2, tt 669.3, fs 688.7, ff 763.6 MHz/V) came from a quadratic fit over the whole S-shaped 0.65-1.4 V curve and are not the slope at 0.9 V. The new values are central differences (+/-50 mV, 27 °C) from the fine sweep in `results/vco/kvco_fine/`. Only the K_VCO column changed; f, spans and tempcos are direct simulation results and are unchanged.

**Real spread: 112 to 1399 ppm/°C — a 12.5× range, not the 3.4-3.2× previously reported.** The worst corner (fs — slow NMOS, fast PMOS) wasn't in Review 1's spot-check at all. The flattest corner (sf) also wasn't checked and would have looked like good news if it had been mistaken for representative.

K_VCO also varies meaningfully by corner: 582 MHz/V (sf) to 1018 MHz/V (fs), a 1.75× spread (corrected from the earlier 1.34×) — smaller than the tempco spread but not negligible for loop-filter sizing robustness across corners (Review 1's loop filter was sized against tt only, and, see `docs/loop_model.md`, with the wrong K_VCO).

## Why the tempco spread looks like this (mechanism, corrected 2026-10-11)

*Earlier wording (wrong):* "the N/P-mismatched corners bracket the range, so current-source balance is the mechanism." That is withdrawn.

V_ctrl drives the NMOS starving gate directly and sets the PMOS bias through the Mnb→Mpb mirror, so the **NMOS overdrive at 0.9 V sets the starving current**. The tempco ranks monotonically with NMOS drive at 0.9 V:

| Corner | NMOS Id @ 0.9 V (µA) | Tempco (ppm/°C) |
|---|---|---|
| sf | 45.1 | 112 |
| ff | 42.8 | 332 |
| tt | 36.2 | 681 |
| ss | 30.3 | 1070 |
| fs | 28.2 | 1399 |

Less overdrive means the Vth drop with temperature is a larger fraction of the overdrive and beats the mobility drop, giving a stronger positive tempco. sf/fs bracket the range only because sky130's skew corners move NMOS Vth by +/-27 mV versus +/-15 mV for ss/ff — not because of N/P balance. Supporting evidence: tt at V_ctrl = 1.4 V (higher overdrive) has f(-40/27/85 °C) = 380.2/358.1/343.7 MHz, i.e. -816 ppm/°C (negative); the tempco changes sign between 0.9 V (+681) and 1.4 V, so a zero-tempco bias point exists, which is textbook and is why f *rises* with T at 0.9 V. This is an interpretation supported by the sign flip and the ordering; there was no separate isolation experiment.

## Consequence for the per-corner compensation decision

This strengthens, not just confirms, the Review 1 decision to define the compensation ratio `C` per-corner rather than as a scalar (`STATUS.md`, `PROJECT_CHARTER.md` decision log). A compensation network sized to the previously-known 3.4× spread would still be off by nearly 4× more at the fs corner. The compensation network (`docs/compensation_model.md`) is derived from the tt fit only so far — corner-specific coefficient refinement is the natural next step before claiming the compensation result generalizes.
