# Cold-Start Acquisition — Fixed and Verified

**Risk (open since Review 1):** the accepted closed-loop lock result (577ns) started from `.ic v(vctrl)=0.85V` — a "coarse-tuned start" inside the VCO's confirmed-oscillating range, not a true cold start. `results/loop/FINDINGS.md` documented that starting from 0V drove the charge pump into a multi-microsecond constant-current dead zone before the VCO ever crossed its oscillation threshold and the divider started toggling.

## The fix

`blocks/charge_pump/charge_pump_acq.spice`: a charge-pump variant that sources/sinks **5× the nominal current** until the divider produces its first edge, then reverts to nominal permanently. "Has the divider ever toggled" is tracked with a B-source-charged capacitor (an integrating one-shot latch) rather than a digital flip-flop — reuses the exact current-injection idiom already proven correct in `charge_pump.spice` (including its node-order polarity lesson), avoiding the metastable-initial-state risk a fresh digital latch would carry.

## Verification: true 0V cold start

`blocks/top/tb_closed_loop_coldstart.spice` — same loop, `.ic v(vctrl)=0` (not 0.85V), 3µs simulation window. **Result: locks in 839ns**, comfortably inside the 2µs spec, on the first simulation attempt (no debug iteration needed).

| Quantity | Cold-start (0V, boosted) | Original (0.85V, unboosted) |
|---|---|---|
| Lock time | 839 ns | 577 ns |
| Settled Vctrl | 0.9002 V | 0.902 V |
| Settled VCO frequency | 226.42 MHz | 227.96 MHz |

The cold-start number is slower (839ns vs 577ns) because it includes real acquisition time the coarse-tuned start skipped — that's expected and correct, not a regression. Trajectory confirms the intended two-phase behavior: vctrl ramps fast (0V→~0.9V by ~596ns, boosted 5×), slightly overshoots (to ~0.975V by 695ns) as the divider's first edges arrive and the boost cuts out, then settles into normal fine-lock dynamics from ~900ns onward — matching the loop model's ~450ns fine-lock prediction added on top of the acquisition ramp.

## Status

This closes the cold-start risk carried since Review 1. Not yet done: sweeping the boost factor (5× was a first reasonable guess, not optimized) or verifying cold-start behavior across corners/PVT — reasonable Review 3 follow-ups, not blockers.
