# Analytical Loop Model — Closed-Loop Design Point

Charge-pump PLL, passive lead-lag filter (R2+C1 series, C2 shunt for ripple), divider ratio N.

> **Erratum (2026-10-11).** The Review 1 version of this file contained an arithmetic error. It put K_VCO in rad/s/V (4.21e9) into `ωn² = Icp·Kvco/(N·C1)` **without the 1/(2π)** of the PFD/charge-pump gain (Icp/2π amps per radian of phase error). That inflated ωn by √(2π) ≈ 2.5×. The values Review 1 reported (fn ≈ 1.98 MHz, ζ ≈ 0.72, PM ≈ 70-72°, BW ≈ 2.85 MHz, "450 ns" lock prediction) were wrong. It was found while cross-checking the loop independently (`scripts/loop_check.py`). The corrected numbers are below. **The transistor-level simulation results (577 ns lock, 839 ns cold start) were never affected** — they come from SPICE, not from this formula. See "What changed / what did not" at the bottom. Also: the K_VCO input (670 MHz/V) was itself wrong; the local value at 0.9 V is ~887 MHz/V (see `results/vco/FINDINGS.md`).

## Design inputs
- K_VCO (tt, 27 °C, V_ctrl = 0.9 V), **local derivative from the fine sweep** (`results/vco/kvco_fine/`, central difference ±50 mV): **887 MHz/V ≈ 890 MHz/V** (= 5.57e9 rad/s/V). Review 1 used 669 MHz/V (= 4.21e9 rad/s/V), a quadratic fit over the whole S-shaped 0.65-1.4 V curve that does not represent the slope at 0.9 V.
- f_osc(0.9 V, tt, 27 °C) = 226.2 MHz (measured) → chosen as the nominal lock point
- N = 8 (fixed divider, per charter's integer-N decision)
- f_ref = f_osc(nominal) / N = 226.2 / 8 = 28.275 MHz
- Icp = 20 µA (design choice, same order as the VCO's own bias current ~58 µA at this bias point)

## Standard 2nd-order type-II CP-PLL formulas (C2 neglected, added after for ripple)

PFD/CP gain is Icp/(2π) A/rad; the VCO gain is K_VCO in rad/s/V (= 2π·K_VCO[Hz/V]). Then

```
ωn² = Icp · Kvco_rad / (2π · N · C1)        (Kvco_rad = 2π · Kvco_Hz, so this is Icp·Kvco_Hz / (N·C1))
ζ   = R2 · C1 · ωn / 2
```

Equivalent form: `ωn² = Icp · K_VCO[Hz/V] / (N · C1)` with K_VCO in Hz/V, **not** rad/s/V.

## Review 1's design (R2 = 1.7 kΩ, C1 = 68 pF, C2 = 6.8 pF, Icp = 20 µA) — recomputed correctly

| Quantity | Review 1 claimed (wrong) | Corrected, K = 669 MHz/V (what R1 designed with) | Corrected, K = 887 MHz/V (measured at 0.9 V) |
|---|---|---|---|
| fn | 1.98 MHz | 0.79 MHz | **0.91 MHz** |
| ζ | 0.72 | 0.29 | **0.33** |
| Phase margin (≈ 100·ζ°, rule of thumb) | 70-72° | ~30° | **~30-33°** (C2 erodes it a little further) |
| Loop bandwidth (≈ 2ζωn) | 2.85 MHz | ~0.45 MHz | ~0.6 MHz |
| "Predicted lock time" | 450 ns | — | — (see below) |

Original design target was fn ≈ 2 MHz, ζ ≈ 0.71. With the correct formula and K = 669 MHz/V, fn = 2 MHz would have needed C1 ≈ 10.6 pF, and with ζ = 0.71 an R2 correspondingly different; the 68 pF / 1.7 kΩ pair that was chosen actually lands at fn ≈ 0.8-0.9 MHz and ζ ≈ 0.3.

**The original loop (R2 = 1.7 kΩ) was underdamped; it has since been retuned to R2 = 3.6 kΩ (see "Retune" below).** The transistor-level lock transient shows it: V_ctrl overshoots to ~0.92 V from the 0.85 V start, and the 0 V cold start rings (`results/loop/FINDINGS_COLDSTART.md`). It still meets the < 2 µs spec in the simulated runs, but it does not have the 70°-class phase margin Review 1 claimed.

## Lock time: what actually matches what

- The old "450 ns analytical prediction" (4τ with τ = 1/(ζωn) = 112 ns) came from the wrong ωn and ζ. It agreed with the 577 ns SPICE result only **by coincidence**; the earlier explanation of the 127 ns gap ("PFD reset delay + discrete CP pumping") was not supported and is withdrawn.
- The corrected ωn, ζ give 4/(ζωn) ≈ 2 µs, which is **not** the relevant metric here: the measured lock is the ±2 %-of-final-value time for a small (50 mV) initial error from 0.85 V, not a settle-to-2 %-of-a-large-step time, so the textbook 4τ formula does not apply to it.
- The meaningful check is independent and numerical: `scripts/loop_check.py` runs an **averaged (phase-domain, continuous-time) behavioural model** of this same loop on the *measured* tt/27 °C tuning curve, starting at 0.85 V, and gets **573 ns** (peak V_ctrl 0.922 V). The full transistor-level transient gives **577 ns**. **So the measured lock time matches an independent model, to <1 %.** (Same model from 0 V with nominal Icp and no boost does not settle — the charge pump saturates, V_ctrl overshoots to 1.79 V — which is consistent with the cold-start problem and the 5× boost fix.)

## What this does NOT yet account for
- The idealized behavioral charge pump (no switch resistance, no mismatch, no charge injection).
- PFD reset delay (~2 inverter delays), not folded into the continuous-time formula.
- C2's effect on phase margin (the third pole erodes margin further than the 100·ζ rule; at ζ ≈ 0.33 this matters, it is not negligible margin as the Review 1 text implied).
- PVT variation. K_VCO varies with corner (local K_VCO at 0.9 V: sf 582, ff 936, tt 887, ss 815, fs 1018 MHz/V), so ωn and ζ (both ∝ √K_VCO) move by roughly -19 % (sf) to +7 % (fs) relative to tt at fixed R2/C1. (Closed-loop corner runs now exist for the retune; see "Five corners" below.)

## Retune: R2 = 1.7 kΩ → 3.6 kΩ (done and verified 2026-10-11)

**Retuned loop filter: R2 = 3.6 kΩ** (C1 = 68 pF, C2 = 6.8 pF, Icp = 20 µA, N = 8, f_ref = 28.275 MHz all unchanged). **Original design: R2 = 1.7 kΩ.** The original numbers below are kept as the "before" of the correction, not deleted.

### Design (K_VCO = 887 MHz/V, tt, 27 °C)

| Quantity | Original (R2 = 1.7 kΩ) | Retuned (R2 = 3.6 kΩ) |
|---|---|---|
| fn | 0.91 MHz | 0.91 MHz (R2 does not enter ωn²) |
| ζ = R2·C1·ωn/2 | 0.33 | **~0.70** |
| Phase margin (≈ 100·ζ°; C2 ignored in the rule of thumb) | ~30-33° | **~65-70°** |

Reason for the choice: the corrected ζ of the original filter was 0.33 (underdamped); ζ ≈ 0.7 needs R2 ≈ 3.6 kΩ at fixed C1, Icp, N. Only R2 = 1.7 k / 3.0 k / 3.6 k were simulated at transistor level (plus an averaged-model sweep over R2 = 1.7-6 kΩ). **The retuned design is not claimed to be optimal, and R2 above 3.6 kΩ was not simulated at transistor level.**

### Transistor-level results, tt, 27 °C, coarse start 0.85 V (nominal charge pump)

Lock = V_ctrl enters and stays within ±2 % of its final value (spec < 2 µs).

| R2 | Lock | Peak V_ctrl | Final f_vco | V_ctrl ripple (last 0.5 µs) |
|---|---|---|---|---|
| 1.7 kΩ (original) | 577 ns | 0.930 V | 227.96 MHz (0.78 % high) | 8.6 mV p-p |
| 3.0 kΩ | 538 ns | - | 226.33 MHz | - |
| **3.6 kΩ (retuned)** | **503 ns** | 0.922 V | 226.18 MHz (0.008 % low) | **0.35 mV p-p** |

### Transistor-level results, tt, 27 °C, TRUE 0 V cold start (5×-boosted charge pump until the first divider edge)

| R2 | Lock | Peak V_ctrl | Final f_vco | V_ctrl ripple (last 0.5 µs) |
|---|---|---|---|---|
| 1.7 kΩ (original) | 839 ns | 1.008 V | 226.42 MHz | 2.6 mV |
| 3.0 kΩ | 1318 ns | - | 225.88 MHz | - |
| **3.6 kΩ (retuned)** | **1352 ns** | 1.001 V | 225.98 MHz (0.1 % low) | 0.35 mV |

### Five corners, coarse 0.85 V start, nominal charge pump (corner runs: `results/loop/retune_corners/`)

| Corner | R2 = 3.6 kΩ (retuned): lock | final f_vco (MHz) | R2 = 1.7 kΩ (original) |
|---|---|---|---|
| tt | 503 ns | 226.18 | 577 ns, 227.96 MHz |
| ff | 241 ns | 226.17 | not settled by 2 µs: 225.17 MHz (0.45 % low) |
| sf (fast-NMOS / slow-PMOS) | 419 ns | 226.39 | not settled by 2 µs: 229.13 MHz (1.3 % high) |
| fs (slow-NMOS / fast-PMOS) | 576 ns | 226.21 | not settled by 2 µs: 228.90 MHz (1.2 % high) |
| ss | 967 ns (5 µs run; settles to V_ctrl = 0.9677 V, 0.1 mV ripple) | 2 µs run: 224.56 (still settling) | 1737 ns in the 5 µs run (3.5 mV ripple); at 2 µs it was 3.6 % low (218.2 MHz) |

**Honest note on the original loop:** at ff/sf/fs/ss the original (R2 = 1.7 kΩ) loop had **not finished settling within the original 2 µs run**, so lock times are not quoted for it at those corners, except ss, where a 5 µs run exists. This is itself a finding: the original loop was slow to settle away from tt, and the "577 ns" figure was a tt-only result. The retuned loop locks inside the 2 µs spec at all five corners and is slowest at ss (967 ns), the corner with the weakest NMOS, which needs V_ctrl ≈ 0.968 V. Corner runs used the coarse 0.85 V start and the plain charge pump (as in the tt coarse run); the 0 V cold start was simulated at tt only.

### Lock-metric sensitivity (±2 % band)

The tt 503 ns figure for R2 = 3.6 kΩ is set by a small overshoot to 0.922 V that sits just outside the ±2 % band (0.918 V) and decays into it at 503 ns. The averaged behavioural model (`scripts/loop_check.py`, with C2 included) has a slightly smaller overshoot, 0.914 V, and enters the band at about 110 ns. The two models agree on the dynamics, but the ±2 % band metric is sensitive at the band edge: a ~8 mV difference in overshoot moves the quoted lock time by hundreds of ns. (At R2 = 1.7 kΩ the averaged model gave 573 ns against 577 ns at transistor level.) Read the lock times together with the peak, final-frequency and ripple columns, not alone.

### Trade-off, stated plainly

- **Better:** damping (ζ 0.33 → 0.70), settling accuracy (coarse-start final frequency error 0.78 % → 0.008 %), V_ctrl ripple (8.6 → 0.35 mV p-p), coarse-start lock at tt (577 → 503 ns), and corner robustness (all five corners inside 2 µs).
- **Worse:** the 0 V cold start is **slower**: 839 → 1352 ns (+61 %). Both are inside the < 2 µs spec, but the margin on the cold start shrinks from 2.4× to 1.5×.

### What the retune does not change

All open-loop results: tempcos, spans, compensation fits, held-out checks, Monte Carlo, K_VCO values, corner-label corrections. They use the free-running VCO with an ideal control voltage, so the loop filter does not enter them.

## Closed-loop testbench design point (`blocks/top/tb_closed_loop.spice`)
- `.ic v(vctrl)=0.7` in the original design note — starts the loop away from the nominal 0.9 V lock point. (The accepted run used 0.85 V; see `results/loop/FINDINGS.md`.) The VCO oscillates down to well below this, only slowly (no hard floor; see `results/vco/FINDINGS.md`).
- f_ref = 28.275 MHz fixed reference.
- Success criterion: vctrl settles near 0.9 V and divider output converges to f_ref (VCO near 226 MHz) within the < 2 µs charter spec.

## What changed / what did not (2026-10-11)

**Changed (formula-derived, now corrected):** fn, ζ, phase margin, loop bandwidth, the "450 ns" prediction, the "~4.4× margin at the analytical level" claim, the "PFD reset delay explains the gap" explanation, and the K_VCO input (670 → ~890 MHz/V).

**Unchanged by the errata pass (direct simulation results):** spans/tempcos (112/332/681/1070/1399 ppm/°C, 12.5× spread), 2nd-order spans, held-out checks, Monte Carlo statistics, lock times 577 ns (coarse start) and 839 ns (0 V cold start), per-corner C values, the tuning range 18 → 358 MHz over 0.65 → 1.40 V (tt), and the empirically refit compensation coefficients.

**Update (retune, 2026-10-11):** the loop filter was then retuned to R2 = 3.6 kΩ. The lock times 577 ns / 839 ns above are the **original R2 = 1.7 kΩ design**; the retuned loop gives 503 ns (coarse) / 1352 ns (0 V cold start). See "Retune" above and `results/loop/FINDINGS_RETUNE.md`. The testbenches `blocks/top/tb_closed_loop*.spice` now instantiate R2 = 3.6 kΩ.
