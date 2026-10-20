#!/usr/bin/env python3
"""Independent check of the loop design numbers (docs/loop_model.md).

1. Standard CP-PLL formulas WITH the 1/(2*pi) phase-detector gain.
2. Averaged behavioural simulation (phase-domain, continuous-time) of the same
   loop driven by the *measured* tt/27C tuning curve, starting at 0.85 V
   and reporting the +/-2% lock time -- to compare against the 577 ns
   from the full transistor-level transient (original R2 = 1.7 kOhm design; the
   retuned R2 = 3.6 kOhm loop is checked in the 'measured local K_VCO' run).
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICP, R2, C1, C2, N, FREF = 20e-6, 1.7e3, 68e-12, 6.8e-12, 8, 28.275e6
tune = json.loads((ROOT / "results/figdata.json").read_text())["tuning"]["tt"]
fine = {0.85: 177.356, 0.875: 202.640, 0.925: 247.507}  # results/vco/kvco_fine
pts = sorted({**{v: f for v, f in tune}, **fine}.items())


def fvco(v):  # MHz, piecewise-linear on measured points, clamped
    if v <= pts[0][0]:
        return pts[0][1] * max(v, 0) / pts[0][0]
    for (v0, f0), (v1, f1) in zip(pts, pts[1:]):
        if v <= v1:
            return f0 + (f1 - f0) * (v - v0) / (v1 - v0)
    return pts[-1][1]


def formulas(k_hz):
    kr = 2 * math.pi * k_hz  # rad/s/V
    wn = math.sqrt(ICP * kr / (2 * math.pi * N * C1))
    z = R2 * C1 * wn / 2
    return wn / 2 / math.pi, z


def lock(v0, dt=0.2e-9, tmax=6e-6):
    vc1, phi, t, settled_at = v0, 0.0, 0.0, None   # phi: ref - div phase (rad)
    trace = []
    while t < tmax:
        i = ICP * max(-1.0, min(1.0, phi / (2 * math.pi)))  # linear PFD range +-2pi, saturates
        v = vc1 + R2 * i
        f = fvco(v) * 1e6
        vc1 += i / C1 * dt
        phi += 2 * math.pi * (FREF - f / N) * dt
        t += dt
        trace.append((t, v))
        if abs(v - 0.9) > 0.018:
            settled_at = None
        elif settled_at is None:
            settled_at = t
    return settled_at, trace



if __name__ == "__main__":
    for label, k in (("Review-1 K_VCO 669 MHz/V", 669e6), ("measured local K_VCO 890 MHz/V", 890e6)):
        fn, z = formulas(k)
        print(f"{label}: fn = {fn/1e6:.2f} MHz, zeta = {z:.2f}, phase margin ~ {math.degrees(math.atan(2*z))-0:.0f} deg (rule)")
    print("Review-1 doc claims: fn = 1.98 MHz, zeta = 0.72  (dropped the 1/2pi in the PD gain)")


    for v0 in (0.85, 0.0):
        s, tr = lock(v0)
        peak = max(v for _, v in tr)
        print(f"averaged-model lock from {v0:.2f} V (nominal I_cp, no boost): "
              f"{s*1e9 if s else float('nan'):.0f} ns, peak V_ctrl {peak:.3f} V")
