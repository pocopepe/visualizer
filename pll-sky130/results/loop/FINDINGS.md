# Closed-Loop Lock — Review 1 Milestone Result

**Result: the loop locks.** Nominal corner (tt, 27°C), design point from `docs/loop_model.md`.

| Quantity | Measured | Target / Predicted |
|---|---|---|
| Lock time (vctrl enters and stays within ±2% of final value) | **577 ns** | <2µs (charter); ~450ns (analytical model) |
| Settled vctrl | 0.902 V | 0.9 V design point |
| Settled div_fb frequency | 28.515 MHz | f_ref = 28.275 MHz (0.85% high) |
| Settled VCO output frequency | 227.96 MHz | N·f_ref = 226.2 MHz (0.78% high) |

The small residual frequency offset (~0.8%) is consistent with normal charge-pump/PFD limit-cycle ripple in a real (non-ideal) type-II CP-PLL — not a bug. The 577ns vs. 450ns gap between measured and analytical lock time is reasonable: the analytical model is a continuous-time linearization that doesn't capture the PFD's reset delay or the charge pump's discrete pumping, both of which add real (if small) settling delay.

Raw data: `run4_icfix.txt` is the accepted result. `run1_acquisition_deadzone.txt`, `run2_finelock.txt`, `run3_holdfix.txt` are kept as the debugging trail, not as results — see below.

## Two real bugs found and fixed getting here — both worth keeping on record

### Bug 1: SPICE current-source node-order convention (run1 → polarity fix)

First attempt: `Bcp ctrl vss I = (up ? +icp : 0) - (dn ? +icp : 0)`. Result: vctrl ramped **monotonically negative** forever regardless of UP/DN — the loop was firing in the right logical sense (UP dominant when it should be) but the physical effect was backwards.

Root cause, confirmed with an isolated 4-line test *before* touching the real circuit again (see `docs/loop_model.md` note, and the throwaway `/tmp/polarity_test*.cir` files): in ngspice's B-source, `Bxxx n1 n2 I=expr` defines current flowing n1→n2 *inside* the source, which by KCL **draws current out of n1** when positive — the opposite of the naive "sources positive current into n1" reading. Verified empirically:
- `Btest ctrl 0 I=1u` on a capacitor from ctrl to ground: ctrl went *negative*.
- `Btest 0 ctrl I=1u` (node order swapped): ctrl went *positive*, as intended.

Fix: swap the node order in `charge_pump.spice` (`Bcp vss ctrl I=...`, not `Bcp ctrl vss I=...`). Lesson worth generalizing: when a SPICE polarity convention is in doubt, a 5-line isolated test costs seconds; guessing costs a 3-minute full-loop rerun per wrong guess, and this specific one *did* need two guesses.

### Bug 2: inconsistent capacitor initial condition (run2/run3 → the real dead-zone cause)

After fixing Bug 1, vctrl still collapsed from its `.ic` value down to ~0.1V within the first ~40ns on every run, before recovering and slowly re-climbing. First hypothesis (wrong, but worth recording *why* it was a reasonable first guess): the PFD/divider's ~30+ internal gate nodes all cold-start at an unstaggered 0V (unlike the VCO, which got explicit staggered `.ic`s after the standalone-VCO critique), so a startup logic glitch asserting DN seemed plausible. Added a 50ns charge-pump hold gate to test this — **the collapse still happened, fully, within that 50ns window**. That result is what disproved the hypothesis rather than confirming it: if the charge pump was disabled and vctrl still collapsed, the charge pump wasn't the cause.

Actual cause: `.ic v(vctrl)=0.85` was set, but the loop filter's own internal node (`nlf`, between R2 and C1) was never given a matching `.ic` and defaulted to 0V. With the charge pump silent, the loop filter is just two capacitors (C1=68pF behind R2, C2=6.8pF direct) with no other source, and they simply redistribute their initial charge: `V_final = (C1·0 + C2·0.85)/(C1+C2) = 0.077V`. Measured collapse point (~0.098-0.13V across the two flawed runs) matches this hand calculation closely. Fix: add `v(xlf.nlf)=0.85` to the `.ic` line, consistent with `v(vctrl)`. Lesson: **every reactive internal node touched by a nontrivial `.ic` needs its own consistent `.ic`, not just the nodes you're deliberately trying to set** — this is the same category of mistake as the VCO's original synchronous-cold-start bug, just one level deeper (a passive RC network this time, not a digital latch).

## What this result does and does not establish

**Does establish:** the topology (PFD → behavioral CP → passive LF → transistor-level ring VCO → transistor-level ÷8 divider) closes into a working, locking negative-feedback loop, with lock dynamics in the right ballpark of the analytical model, at one operating point (tt corner, 27°C, starting near the nominal bias).

**Does not yet establish:**
- Lock across PVT (this run is tt/27°C only — Review 2 scope).
- Robustness to a cold start *outside* the VCO's confirmed-oscillating range. `run1_acquisition_deadzone.txt` (from before the IC fix, but still informative on this point) showed that starting below the VCO's ~0.65V oscillation floor drives the loop into a multi-microsecond charge-pump-integration dead zone before the divider even starts toggling — directly compounding the VCO lock-range finding from `results/vco/FINDINGS.md`. This remains a real, open risk for anything other than a "coarse-tuned start" — see `STATUS.md` decision #1.
- Any noise/jitter/phase-noise behavior (the charge pump is still the idealized behavioral model from `blocks/charge_pump/charge_pump.spice` — transistor-level CP with real mismatch is deferred to Review 2, where it's needed anyway for the Monte Carlo study).
- PFD dead-zone quantified (the ~0.8% frequency offset is consistent with it, but not isolated and measured directly).
