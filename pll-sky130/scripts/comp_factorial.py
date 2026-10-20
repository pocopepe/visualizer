#!/usr/bin/env python3
"""Compensation fit + verification on the textbook factorial corners.

Method (per corner), all with the behavioural correction vctrl_eff = vctrl + k1*(T-27) + k2*(T-27)^2:
  1. Surface:  f(T, V) at T in {-40,-20,0,27,50,85} and V in {0.85, 0.90, 0.95} (blocks/vco/tb_comp_template.spice, k=0).
  2. Required correction dV*(T): the V shift that returns f(T, 0.9 + dV) to f(27 C, 0.9), by quadratic interpolation in V.
  3. Least-squares fit of dV*(T) to k1*dT (1st order) and k1*dT + k2*dT^2 (2nd order), dT = T - 27.
  4. Verify by SIMULATING the compensated VCO at the 6 fit temperatures (1st and 2nd order) and at 4 held-out
     temperatures (-30, 10, 40, 70 C) for the 2nd-order coefficients.
Reports span = (max-min)/f27 and max |deviation| from f27, in %, for baseline / 1st / 2nd order and held-out.
Usage: comp_factorial.py [corner ...]   (default: ntpt nspt nspf ntps ntpf nfps nfpt)
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from make_figdata import freq  # noqa: E402

OUT = ROOT / "results/comp/factorial"
FACT = str(ROOT / "env/sky130_factorial.lib.spice")
PDKLIB = os.environ.get("SPICE_MODELS", "/home/pocopepe/pdk/volare/sky130/versions/c6d73a35f524070e85faff4a6a9eef49553ebc2b/sky130B/libs.tech/ngspice/sky130.lib.spice")
TEMPLATE = (ROOT / "blocks/vco/tb_comp_template.spice").read_text()
VCO_INC = str(ROOT / "blocks/vco/vco_ring.spice")
TEMPS = [-40, -20, 0, 27, 50, 85]
HOLD = [-30, 10, 40, 70]


def point(corner, T, V, k1=0.0, k2=0.0):
    tag = f"{corner}_T{T}_Vc{V}_k1{k1:.6e}_k2{k2:.6e}"
    d = OUT / "raw"
    d.mkdir(parents=True, exist_ok=True)
    txt, cir = d / f"{tag}.txt", d / f"{tag}.cir"
    if not txt.exists():
        lib, cname = (PDKLIB, corner[4:]) if corner.startswith("pdk_") else (FACT, corner)   # pdk_sf / pdk_fs = the PDK's own skew corners
        s = (TEMPLATE.replace("__SPICE_MODELS__", lib).replace("__CORNER__", cname).replace("__TEMP__", str(T))
             .replace("__VCTRL__", str(V)).replace("__TSTEP__", "10p").replace("__TSTOP__", "400n")
             .replace("__K1__", f"{k1:.6e}").replace("__K2__", f"{k2:.6e}").replace("__OUTFILE__", str(txt))
             .replace('"vco_ring.spice"', f'"{VCO_INC}"'))
        cir.write_text(s)
        subprocess.run(["ngspice", "-b", str(cir)], stdin=subprocess.DEVNULL, capture_output=True, timeout=3600, cwd=ROOT)
    return freq(str(txt))


def solve_v(vs, fs, target):
    """V (nearest 0.9) where the quadratic through (vs, fs) equals target."""
    import numpy as np
    c = np.polyfit(vs, fs, 2)
    c[2] -= target
    roots = [r.real for r in np.roots(c) if abs(r.imag) < 1e-9 and 0.8 < r.real < 1.0]
    return min(roots, key=lambda r: abs(r - 0.9)) - 0.9


def lsq(dT, dv, order):
    s11 = sum(x * x for x in dT)
    if order == 1:
        return sum(x * y for x, y in zip(dT, dv)) / s11, 0.0
    s12 = sum(x ** 3 for x in dT)
    s22 = sum(x ** 4 for x in dT)
    b1 = sum(x * y for x, y in zip(dT, dv))
    b2 = sum(x * x * y for x, y in zip(dT, dv))
    det = s11 * s22 - s12 * s12
    return (b1 * s22 - b2 * s12) / det, (s11 * b2 - s12 * b1) / det


def metrics(f, f27):
    dev = [(v - f27) / f27 * 100 for v in f]
    return {"span_pct": (max(f) - min(f)) / f27 * 100, "maxdev_pct": max(abs(x) for x in dev)}


def pmap(ex, jobs):
    return list(ex.map(lambda j: point(*j), jobs))


def run_all(corners):
    res = {}
    with ThreadPoolExecutor(15) as ex:
        surf = {}
        jobs = [(c, T, V) for c in corners for T in TEMPS for V in (0.85, 0.9, 0.95)]
        for j, f in zip(jobs, pmap(ex, jobs)):
            surf[j] = f
        fits = {}
        jobs = []
        for c in corners:
            f27 = surf[(c, 27, 0.9)]
            dT = [T - 27 for T in TEMPS if T != 27]
            dv = [solve_v((0.85, 0.9, 0.95), [surf[(c, T, V)] for V in (0.85, 0.9, 0.95)], f27) for T in TEMPS if T != 27]
            fits[c] = (dT, dv, {o: lsq(dT, dv, o) for o in (1, 2)})
            for o in (1, 2):
                jobs += [(c, T, 0.9, *fits[c][2][o]) for T in TEMPS]
            jobs += [(c, T, 0.9, *fits[c][2][2]) for T in HOLD]
        ver = {}
        for j, f in zip(jobs, pmap(ex, jobs)):
            ver[(j[0], j[1], round(j[3], 12), round(j[4], 12))] = f
    for c in corners:
        dT, dv, co = fits[c]
        f27 = surf[(c, 27, 0.9)]
        r = {"corner": c, "f27_MHz": f27, "dV_required_mV": {str(t + 27): round(v * 1e3, 3) for t, v in zip(dT, dv)},
             "baseline": metrics([surf[(c, T, 0.9)] for T in TEMPS], f27)}
        for o in (1, 2):
            k1, k2 = co[o]
            f = [ver[(c, T, round(k1, 12), round(k2, 12))] for T in TEMPS]
            r[f"order{o}"] = {"k1": k1, "k2": k2, **metrics(f, f27), "f": dict(zip(map(str, TEMPS), f))}
        k1, k2 = co[2]
        dev = [(ver[(c, T, round(k1, 12), round(k2, 12))] - f27) / f27 * 100 for T in HOLD]
        r["holdout"] = {"maxdev_pct": max(abs(x) for x in dev), "dev_pct": dict(zip(map(str, HOLD), dev))}
        r["compensation_ratio_C"] = r["baseline"]["span_pct"] / r["order2"]["span_pct"]
        r["meets_0p3pct"] = r["order2"]["maxdev_pct"] <= 0.3
        res[c] = r
    return [res[c] for c in corners]


if __name__ == "__main__":
    corners = sys.argv[1:] or ["ntpt", "nspt", "nspf", "ntps", "ntpf", "nfps", "nfpt"]
    OUT.mkdir(parents=True, exist_ok=True)
    results = run_all(corners)
    json.dump(results, open(OUT / "factorial_comp.json", "w"), indent=1)
    print(f"{'corner':<6} {'base span':>9} {'1st span':>9} {'2nd span':>9} {'2nd maxdev':>10} {'holdout':>8} {'C':>6}  k1 (V/C)  k2 (V/C^2)")
    for r in results:
        print(f"{r['corner']:<6} {r['baseline']['span_pct']:9.2f} {r['order1']['span_pct']:9.2f} {r['order2']['span_pct']:9.2f} "
              f"{r['order2']['maxdev_pct']:10.2f} {r['holdout']['maxdev_pct']:8.2f} {r['compensation_ratio_C']:6.2f}  "
              f"{r['order2']['k1']:.3e} {r['order2']['k2']:.3e}")
