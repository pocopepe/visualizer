# Sensitivity Analysis — What Drives the Tempco Spread

Corner-level analysis using the already-collected 5-corner grid (`results/vco/grid5corner.csv`), not a new per-device-parameter Monte Carlo campaign — a full tornado chart (isolating each individual BSIM parameter's contribution) would need a dedicated one-parameter-at-a-time sweep, deferred to Review 3 if a finer breakdown is needed. This is the data-driven insight available without new simulation.

> **Erratum (2026-10-11).** The first version of this note had the sf/fs labels backwards and attributed the
> spread to N/P current-source balance. Both are corrected below; the measured tempco numbers are unchanged.

## The corners, decoded

In this PDK (sky130B, volare c6d73a35) the `sf` corner lowers NMOS Vth by 27 mV (mobility +5 %) and raises |Vth| of the PMOS by 37 mV (mobility -10 %): **sf = fast-NMOS / slow-PMOS**. `fs` is the reverse: **slow-NMOS / fast-PMOS**. The ss/ff corners move NMOS Vth by only +/-15 mV, so the skew corners are *more extreme on the NMOS* than ss/ff.

NMOS drive current of a single device (W/L = 2/0.5, |Vgs| = 0.9 V, 27 C), against the uncompensated tempco from the grid:

| Corner | NMOS | PMOS | NMOS Id (uA) | Tempco |
|---|---|---|---|---|
| sf | fast | slow | 45.1 | +112 ppm/C |
| ff | fast | fast | 42.8 | +332 ppm/C |
| tt | typical | typical | 36.2 | +681 ppm/C |
| ss | slow | slow | 30.3 | +1070 ppm/C |
| fs | slow | fast | 28.2 | +1399 ppm/C |

## The finding

**Tempco ranks exactly with NMOS drive at the 0.9 V bias point.** V_ctrl drives the NMOS starving gate directly and sets the PMOS bias through the Mnb -> Mpb mirror, so NMOS overdrive sets the ring current. With less overdrive, the threshold-voltage drop with temperature is a larger fraction of the overdrive and outweighs the mobility drop, so frequency rises with temperature more steeply. sf and fs bracket the whole range only because sky130's skew corners shift NMOS Vth further than ss/ff do.

Supporting check (`results/vco/floor_check/`): at V_ctrl = 1.4 V (tt) the tempco is **-816 ppm/C** (f = 380.2 / 358.1 / 343.7 MHz at -40 / 27 / 85 C), so the sign flips between 0.9 V and 1.4 V -- a zero-tempco bias point exists, which is the textbook behaviour behind this ordering.

This explains why a compensation network tuned for the tt bias point misses at the other corners and why per-corner refitting was necessary (`results/comp/percorner_*`).

## What this does NOT establish
- Which specific BSIM parameter (Vth tempco vs mobility tempco) dominates quantitatively -- the NMOS-overdrive ordering and the sign flip support the explanation but it was not isolated with a one-parameter-at-a-time sweep.
- Whether a redesigned bias generator (e.g., biasing nearer the zero-tempco point) would reduce the underlying sensitivity rather than just compensating around it — a real Review 3 candidate if pursued.
