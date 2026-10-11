# Cold-Start Acquisition — Fixed and Verified

> **Retune note (2026-10-11).** The numbers in this file are for the **original loop filter, R2 = 1.7 kΩ**, kept as the "before". With the retuned **R2 = 3.6 kΩ** the same 0 V cold start (tt, 27 °C, same 5× boosted pump) locks in **1352 ns** (peak V_ctrl 1.001 V, final f_vco 225.98 MHz, 0.1 % low, 0.35 mV ripple) versus **839 ns** here (peak 1.008 V, 226.42 MHz, 2.6 mV). **The cold start is slower with the retune (+61 %)**; both are inside the 2 µs spec. R2 = 3.0 kΩ gave 1318 ns / 225.88 MHz. Cold start was simulated at tt only. See `results/loop/FINDINGS_RETUNE.md`. `blocks/top/tb_closed_loop_coldstart.spice` now instantiates r2=3.6k.

**Risk (open since Review 1):** the accepted closed-loop lock result (577ns) started from `.ic v(vctrl)=0.85V` — a "coarse-tuned start" inside the VCO's usable range, not a true cold start. `results/loop/FINDINGS.md` documented that starting from 0V drove the charge pump into a multi-microsecond constant-current dead zone before the VCO reached a useful frequency (it is under 18 MHz below ~0.65 V and sub-MHz at 0.5 V; there is no hard oscillation floor, corrected 2026-10-11) and the divider started toggling. The PFD therefore sees only REF edges and the nominal 20 µA pump is too slow to climb out.

## The fix

`blocks/charge_pump/charge_pump_acq.spice`: a charge-pump variant that sources/sinks **5× the nominal current** until the divider produces its first edge, then reverts to nominal permanently. "Has the divider ever toggled" is tracked with a B-source-charged capacitor (an integrating one-shot latch) rather than a digital flip-flop — reuses the exact current-injection idiom already proven correct in `charge_pump.spice` (including its node-order polarity lesson), avoiding the metastable-initial-state risk a fresh digital latch would carry.

## Verification: true 0V cold start

`blocks/top/tb_closed_loop_coldstart.spice` — same loop, `.ic v(vctrl)=0` (not 0.85V), 3µs simulation window. **Result (original R2 = 1.7 kΩ): locks in 839ns**, comfortably inside the 2µs spec, on the first simulation attempt (no debug iteration needed).

| Quantity (original R2 = 1.7 kΩ) | Cold-start (0V, boosted) | Original (0.85V, unboosted) |
|---|---|---|
| Lock time | 839 ns | 577 ns |
| Settled Vctrl | 0.9002 V | 0.902 V |
| Settled VCO frequency | 226.42 MHz | 227.96 MHz |

The cold-start number is slower (839ns vs 577ns) because it includes real acquisition time the coarse-tuned start skipped — that's expected and correct, not a regression. Trajectory confirms the intended two-phase behavior: vctrl ramps fast (0V→~0.9V by ~596ns, boosted 5×), slightly overshoots (to ~0.975V by 695ns) as the divider's first edges arrive and the boost cuts out, then settles into normal fine-lock dynamics from ~900ns onward — consistent with the fine-lock time of the 0.85 V run. (An earlier version cited the "~450 ns" loop-model prediction here; that figure is withdrawn, see `docs/loop_model.md`.) Note the overshoot/ringing is expected: the original loop is underdamped (ζ ≈ 0.33 corrected; ζ ≈ 0.70 after the R2 retune). The independent averaged model (`scripts/loop_check.py`) shows that *without* the 5× boost, starting from 0 V, the loop does not settle (the charge pump saturates and V_ctrl overshoots to 1.79 V), consistent with the cold-start problem this fix addresses.

## Status

This closes the cold-start risk carried since Review 1. Not yet done: sweeping the boost factor (5× was a first reasonable guess, not optimized) or verifying cold-start behavior across corners/PVT — reasonable Review 3 follow-ups, not blockers.
