# Analytical Loop Model — Review 1 Closed-Loop Design Point

Charge-pump PLL, passive lead-lag filter (R2+C1 series, C2 shunt for ripple), divider ratio N.

## Design inputs (measured, not assumed)
- Kvco ≈ 670 MHz/V = 4.21e9 rad/(s·V) — fit derivative at Vctrl=0.9V, tt corner, from `results/vco/FINDINGS.md`
- f_osc(0.9V, tt, 27°C) = 226.2 MHz (measured) → chosen as the nominal lock point
- N = 8 (fixed divider, per charter's integer-N decision)
- f_ref = f_osc(nominal) / N = 226.2 / 8 = 28.275 MHz
- Icp = 20 µA (design choice, same order of magnitude as the VCO's own bias current ~58µA at this bias point)

## Standard 2nd-order type-II CP-PLL formulas (C2 neglected for the dominant-pole design, added after for ripple)

```
ωn² = Icp · Kvco / (N · C1)
ζ   = (R2/2) · sqrt(Icp · Kvco · C1 / N)
```

Target: fn ≈ 2 MHz (ωn = 2π×2e6 = 1.257e7 rad/s), ζ ≈ 0.71 (near-critical damping, good phase margin).

Solving for C1:
```
C1 = Icp·Kvco / (N·ωn²) = (2e-5 × 4.21e9) / (8 × 1.579e14) ≈ 66.7 pF  →  round to 68 pF
```
Solving for R2 (using the rounded C1):
```
R2 = 2ζ / sqrt(Icp·Kvco·C1/N) ≈ 1688 Ω  →  round to 1.7 kΩ
```
C2 (ripple/3rd-pole, standard C1/10 placement): **6.8 pF**

## Predicted loop dynamics with rounded values (R2=1.7k, C1=68p, C2=6.8p, Icp=20µA)

| Quantity | Value |
|---|---|
| ωn (recomputed) | 1.244e7 rad/s → fn ≈ 1.98 MHz |
| ζ (recomputed) | 0.72 |
| Loop bandwidth (≈2ζωn) | ω_BW ≈ 1.79e7 rad/s → f_BW ≈ 2.85 MHz |
| Phase margin (≈100·ζ° for ζ<1, rule of thumb) | ≈ 70-72° |
| Settling time constant τ = 1/(ζωn) | ≈ 112 ns |
| Predicted lock time (≈4τ to ~2% settling) | **≈ 450 ns** |

Charter target is <2µs — this design has ~4.4× margin at the analytical level, before any real-circuit second-order effects (charge-pump nonidealities, PFD dead zone, divider delay) are accounted for.

## What this does NOT yet account for
- The idealized behavioral charge pump (no switch resistance, no mismatch, no charge injection).
- PFD reset delay (~2 inverter delays) is a real, if small, extra loop delay not folded into the classical continuous-time formula above.
- C2's effect on phase margin (a third pole always erodes margin somewhat; not iterated here since ζ came out comfortably >0.7 with margin to spare).
- Any PVT variation — this is a single-corner (tt), single-temperature (27°C) design point, matching Review 1 scope. K_VCO itself varies with corner (see `results/vco/FINDINGS.md`), so R2/C1 sized here will give different fn/ζ at ss/ff; that's explicitly Review 2 (PVT sweep + compensation) territory, not re-derived per-corner here.

## Closed-loop testbench design point (`blocks/top/tb_closed_loop.spice`)
- `.ic v(vctrl)=0.7` — starts the loop away from the nominal 0.9V lock point but still inside the VCO's confirmed-oscillating range (≥0.65V per `results/vco/FINDINGS.md`), so there's a real pull-in transient to observe and measure, without hitting the VCO's oscillation-startup problem (see charter decision on the V_ctrl floor).
- f_ref = 28.275 MHz fixed reference.
- Success criterion: vctrl settles near 0.9V and divider output frequency converges to f_ref (i.e., VCO settles near 226 MHz), within a time comparable to the ~450ns analytical prediction (order-of-magnitude agreement expected, not exact — the idealizations above will shift the real number).
