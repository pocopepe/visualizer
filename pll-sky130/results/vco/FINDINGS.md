# VCO Baseline Characterization — Findings

**Status:** First real simulated results, post-critique revision 2. sky130B, tt/ss/ff corners, ngspice-42.
**Circuit:** 5-stage current-starved ring oscillator, `blocks/vco/vco_ring.spice`.
**Reproduce:** `source env/pdk.env && ./scripts/run_sweep.sh <outdir> <jobs> <points...>` then `python3 scripts/compile_vco_results.py <outdir> <csv>`.

This is not a clean-room result — it went through one adversarial-review pass (a subagent tasked to critique it as a skeptical reviewer/thesis committee member would) before these numbers were trusted. That review caught real bugs, not just style issues; see "What the critique pass changed" below. Treat that as the standard for every subsequent block, not a one-off.

---

## Headline numbers

| Quantity | Value | Caveat |
|---|---|---|
| K_VCO (fit derivative @ 0.9V, tt, 27°C) | ~670 MHz/V | Curve is measurably nonlinear (quadratic fit); a two-point secant elsewhere on the curve gives a visibly different number. Always state the bias point. |
| Uncompensated tempco, tt corner (endpoint secant, -40→85°C) | +681 ppm/°C | **Not constant** — per-interval local slope ranges from +1123 ppm/°C (cold end) to +352 ppm/°C (hot end), a >3× spread. See table below. |
| Uncompensated tempco, **ss** corner | +1070 ppm/°C | |
| Uncompensated tempco, **ff** corner | +332 ppm/°C | |
| Minimum Vctrl for sustained oscillation (tt, 27°C) | between 0.60 V and 0.65 V | 0.65V confirmed oscillating (17.975 MHz); 0.50/0.55/0.60V did not complete within a 240s/3µs simulation budget — consistent with approaching a bifurcation where settling time diverges, not just "needs more time." |

## The finding that actually matters most right now

**The tempco magnitude varies more than 3× across process corners (332 ppm/°C at ff vs. 1070 ppm/°C at ss, vs. 681 ppm/°C at tt).** This was a direct spot-check of the critique's corner-blindness concern (3 temperature points × ss/ff, cheap to run) and it came back positive: a compensation network sized against the tt curve alone would be off by more than 3× at the ss corner. This has to be accounted for before compensation-network topology is finalized at Review 2 — either the network needs corner-tracking (e.g., its own PTAT slope derived from the same process parameters driving the VCO's drift, so the two naturally track), or the charter's compensation ratio `C` needs to be defined per-corner, `C(corner)`, rather than as a single scalar. Decide this explicitly; don't let it default silently to "designed against tt."

## A second finding worth flagging to Dr. Bindu directly

**The VCO does not sustain oscillation down to the charter's mandated V_ctrl floor of 0.27V** (charter §4: lock range requires V_ctrl ∈ [0.15·VDD, 0.85·VDD] = [0.27V, 1.53V]). At tt/27°C, oscillation was confirmed at 0.65V and lost somewhere between 0.60V and 0.65V — and this is the *best-behaved* corner/temperature; ss + cold temperature will starve the bias current further and can only push this boundary higher, not lower. Two ways to close this gap, to be resolved before charge-pump/loop-filter sizing at Review 2:
1. Resize the bias generator (`wcs`/`lcs` in `vco_ring.spice`) so meaningful current still flows at low Vctrl — likely needs a lower threshold-adjacent design or a level-shifted control path.
2. Or, revise the charter's V_ctrl floor to match what this topology can actually deliver, and re-derive the lock-range implications.
Either is fine; leaving it unresolved is not — it's a contradiction between a locked spec and a measured result, sitting in our own data.

## Per-interval tempco (tt corner, Vctrl=0.9V) — why the average is misleading

| Interval | Local tempco |
|---|---|
| -40 → -20°C | +1123 ppm/°C |
| -20 → 0°C | +924 ppm/°C |
| 0 → 27°C | +722 ppm/°C |
| 27 → 50°C | +537 ppm/°C |
| 50 → 85°C | +352 ppm/°C |

Concave/sublinear, as expected from BSIM mobility/threshold temperature behavior. The single "+681 ppm/°C average" figure is the -40↔85°C endpoint secant — useful as a one-line summary, not as the number a compensation network gets designed against. A degree-2 fit is in `compile_vco_results.py`'s output; use its derivative at whatever operating temperature matters, not the secant.

## Known limitations (open, deliberately deferred)

- **Unloaded output.** The measured tuning curve is for the ring driving nothing (the `Eout` block is an ideal zero-load unity buffer). Real frequency will shift once this VCO drives an actual PFD/divider input capacitance. Re-characterize once the loop is assembled.
- **Steady-state overshoot beyond the rails** (~-0.13V to ~2.0V observed, confirmed genuine and not a startup artifact — see "What the critique pass changed" below) is a property of the unloaded ring node and may not persist once loaded. Flagged, not yet explained or fixed.
- **`period_regularity_frac` reads 0.0000 everywhere.** This is expected and correct for a noiseless deterministic simulation — it is not a jitter or phase-noise measurement (renamed from `jitter_frac` specifically to prevent that misreading). A real jitter/phase-noise estimate needs a noise source and is Review 2/3 scope per the charter.
- **Device sizing is a first-pass, unswept guess** (inverter 1.0/0.5µm, current-source/bias devices 2.0/0.5µm). Not yet justified by a sizing sweep. Numbers above are rounded to reflect that; don't over-read the 3rd significant figure.
- **PVT coverage is a 3-point spot-check (ss/ff at -40/27/85°C only), not the full corner × temperature grid.** That's Review 2 scope (CACE-driven). This spot-check exists only to catch a qualitative surprise before compensation design starts, which it did (see above).

## What the critique pass changed (netlist rev1 → rev2)

An adversarial-review subagent read the rev1 netlist/scripts/results cold and flagged issues before any of these numbers were trusted. Concrete corrections made in response, each of which changed either the produced numbers or their reliability:

1. **`v_min`/`v_max` were computed on the pre-skip (startup-transient-included) window.** Fixed to use the post-skip steady-state window only. Result: the rail-exceeding swing (-0.13V to 2.0V) persisted even post-fix — confirmed as a real steady-state property, not a startup artifact.
2. **Cold-start `uic` with all nodes implicitly at 0V** meant all 5 stages switched synchronously from an identical state — a known way to manufacture spurious ringing unrelated to the true limit cycle. Fixed with staggered `.ic` guesses across the ring nodes.
3. **A 4-period frequency estimate (Vctrl=0.65V) was reported with no confidence flag**, and a fixed 400ns window was applied uniformly regardless of expected frequency, starving exactly the near-threshold points where settling time is longest. Fixed: added a `low_confidence` flag (<10 periods) in the extraction script, and used point-specific longer windows (up to 3µs) for low-Vctrl points.
4. **Supply current was entirely missing** despite being an explicit Review-1 deliverable in the charter. Added via a series zero-volt ammeter and `.meas ... avg`.
5. **`jitter_frac` was a misleading name** for a quantity that isn't jitter in any physical sense (fully deterministic sim, no noise source) — renamed to `period_regularity_frac` with an explicit comment before it could get silently promoted into a phase-noise claim later.
6. **A K_VCO/tempco secant computed from two arbitrary points on a visibly nonlinear curve** was being reported as if it were a single well-defined number. Replaced with a proper polynomial fit, per-interval breakdown, and an explicit warning against quoting a bias-point-independent scalar.
7. **A PMOS pin-order inconsistency** in `vco_ring.spice` (`Xmp_cs`/`Xmp_inv` had source/drain swapped relative to sky130's `(d g s b)` convention, inconsistent with the correctly-wired bias-generator PMOS in the same file) — didn't change simulated results here (BSIM doesn't care about the label, and no parasitic-area terms were being passed), but was fixed before it could become a real bug once this topology reaches layout/LVS.

Two follow-on engineering bugs surfaced *while implementing* the fixes above (not part of the critique itself, just standard ngspice control-language quirks): `{PARAM}` brace substitution doesn't resolve inside `.control`-block `tran`/`meas` commands, only in top-level `.tran`/`.meas` statements — fixed by moving both to top level and using `run` inside `.control` to execute them.
