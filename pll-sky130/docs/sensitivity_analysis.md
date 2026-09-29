# Sensitivity Analysis — What Drives the Tempco Spread

Corner-level analysis using the already-collected 5-corner grid (`results/vco/grid5corner.csv`), not a new per-device-parameter Monte Carlo campaign — a full tornado chart (isolating each individual BSIM parameter's contribution) would need a dedicated one-parameter-at-a-time sweep, deferred to Review 3 if a finer breakdown is needed. This is the data-driven insight available without new simulation.

## The corners, decoded

sky130's 5 standard corners aren't a full N×P factorial — they're the specific combinations foundries use for signoff: tt (typical/typical), ff (fast/fast), ss (slow/slow), sf (slow-N/fast-P), fs (fast-N/slow-P).

| Corner | NMOS | PMOS | Uncompensated tempco |
|---|---|---|---|
| sf | slow | fast | +112 ppm/°C |
| ff | fast | fast | +332 ppm/°C |
| tt | typical | typical | +681 ppm/°C |
| ss | slow | slow | +1070 ppm/°C |
| fs | fast | slow | +1399 ppm/°C |

## The finding

**The two "mismatched" corners (sf, fs) bracket the *entire* range — both the flattest (sf) and the steepest (fs) tempco.** The two "matched-speed" corners (ff, ss) sit inside that range, not at the extremes. If tempco were driven mainly by *absolute* device speed (how fast the corner is, independent of which device type), the matched corners would be the extremes and the mismatched ones would land in between — the opposite of what's measured.

This points to the tempco being driven substantially by the **relative balance between the ring's PMOS current-source path and NMOS current-source path** (`Mp_cs` vs `Mn_cs` in `vco_ring.spice`), not by either device's absolute speed alone. When N and P are mismatched (sf, fs), that balance shifts hardest with temperature — in one direction it happens to partially self-cancel (sf, flattest), in the other it compounds (fs, steepest). This is consistent with — and gives a circuit-level explanation for — why a temperature-compensation network tuned only for the typical (tt) balance point misses badly at the mismatched corners: it's correcting a symptom (the tt-specific drift curve) rather than the underlying cause (N/P balance sensitivity), which is exactly why per-corner refitting was necessary rather than optional polish (`results/comp/percorner_*` results).

## What this does NOT establish
- Which specific BSIM parameter (Vt mismatch, mobility tempco, etc.) is the root cause of the N/P balance sensitivity — that needs a per-parameter sweep, not corner-level data.
- Whether a redesigned bias generator (e.g., a current mirror less sensitive to N/P mismatch) would reduce the underlying sensitivity rather than just compensating around it — a real Review 3 candidate if pursued.
