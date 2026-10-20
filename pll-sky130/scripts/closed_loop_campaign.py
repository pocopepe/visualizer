#!/usr/bin/env python3
"""Closed-loop lock campaign (retuned loop filter R2 = 3.6k) across process corners, start conditions and temperature.

Cases: coarse start (0.85 V) and true 0 V cold start (boosted CP) at all 9 textbook corners + the PDK sf/fs,
plus cold start at -40 / 85 C for the three corner extremes.  One ngspice process per case (1 thread each).
Outputs results/loop/campaign/<case>.json (+ raw .txt, gitignored) and results/loop/campaign/summary.csv.
Usage: closed_loop_campaign.py [--analyse-only]
"""
import csv, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results/loop/campaign"
PDKLIB = os.environ.get("SPICE_MODELS", "/home/pocopepe/pdk/volare/sky130/versions/c6d73a35f524070e85faff4a6a9eef49553ebc2b/sky130B/libs.tech/ngspice/sky130.lib.spice")
FACT = str(ROOT / "env/sky130_factorial.lib.spice")
TB = {"coarse": ROOT / "blocks/top/tb_closed_loop.spice", "cold": ROOT / "blocks/top/tb_closed_loop_coldstart.spice"}
TSTOP_NS = 5000
F_TARGET, V_BAND = 226.2, 0.02


def cases():
    fact = [f"n{n}p{p}" for n in "stf" for p in "stf"]
    cs = []
    for c in fact:
        for kind in ("coarse", "cold"):
            cs.append((c, "fact", 27, kind))
    for c in ("sf", "fs"):
        for kind in ("coarse", "cold"):
            cs.append((c, "pdk", 27, kind))
    for c in ("nsps", "ntpt", "nfpf"):
        for T in (-40, 85):
            cs.append((c, "fact", T, "cold"))
    return cs


def tag(c):
    return f"{'pdk_' if c[1] == 'pdk' else ''}{c[0]}_T{c[2]}_{c[3]}"


def run(c):
    t = tag(c)
    OUT.mkdir(parents=True, exist_ok=True)
    txt, cir = OUT / f"{t}.txt", OUT / f"{t}.cir"
    s = TB[c[3]].read_text()
    lib = FACT if c[1] == "fact" else PDKLIB
    s = s.replace('.lib "__SPICE_MODELS__" tt', f'.lib "{lib}" {c[0]}').replace(".temp 27", f".temp {c[2]}")
    s = s.replace("results_loop_coldstart.txt", str(txt)).replace("results_loop.txt", str(txt))
    s = s.replace("v(vctrl) v(vco_out) v(div_fb) v(up) v(dn)", "v(vctrl) v(vco_out)")
    import re
    s = re.sub(r"\.tran 20p \d+n uic", f".tran 20p {TSTOP_NS}n uic", s)
    assert str(txt) in s and "r2=3.6k" in s and f".tran 20p {TSTOP_NS}n" in s, t
    s = s.replace("\n.control\n", "\n.control\n  set num_threads=1\n", 1)
    cir.write_text(s)
    subprocess.run(["ngspice", "-b", str(cir)], stdin=subprocess.DEVNULL, capture_output=True, timeout=7200, cwd=ROOT)
    return analyse(c)


def analyse(c):
    t = tag(c)
    a = np.loadtxt(OUT / f"{t}.txt")
    tn, v, vo = a[:, 0] * 1e9, a[:, 1], a[:, 3]
    m = tn > tn.max() - 500
    vfin = float(v[m].mean())
    out_band = tn[np.abs(v - vfin) > V_BAND * vfin]
    lock = float(out_band.max()) if len(out_band) else 0.0
    # f_vco over the last 500 ns from rising crossings of 0.9 V
    x, tt = vo[m], tn[m]
    idx = np.where((x[:-1] < 0.9) & (x[1:] >= 0.9))[0]
    f = float(1e3 / np.diff(tt[idx]).mean()) if len(idx) > 2 else float("nan")
    last = tn > tn.max() - 1000
    drift = float(abs(v[last][-200:].mean() - v[last][:200].mean()))  # settled?  (V change over the last 1 us)
    r = dict(case=t, corner=c[0], lib=c[1], temp_C=c[2], start=c[3], lock_ns=round(lock, 1), vctrl_final_V=round(vfin, 4),
             f_vco_MHz=round(f, 3), f_err_pct=round((f / F_TARGET - 1) * 100, 3), ripple_mV=round(float((v[m].max() - v[m].min()) * 1e3), 2),
             peak_V=round(float(v[tn > 50].max()), 3), drift_last_us_mV=round(drift * 1e3, 2), tstop_ns=int(tn.max()),
             settled=bool(lock < tn.max() - 1000 and drift < 0.005))
    (OUT / f"{t}.json").write_text(json.dumps(r, indent=1))
    return r


if __name__ == "__main__":
    cs = cases()
    if "--analyse-only" in sys.argv:
        res = [analyse(c) for c in cs]
    else:
        with ThreadPoolExecutor(15) as ex:
            res = list(ex.map(run, cs))
    with open(OUT / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, res[0].keys()); w.writeheader(); w.writerows(res)
    for r in res:
        print(f"{r['case']:<22} lock {r['lock_ns']:>7} ns  f {r['f_vco_MHz']:>8} MHz ({r['f_err_pct']:+.2f}%)  Vlock {r['vctrl_final_V']:.3f}  ripple {r['ripple_mV']} mV  settled={r['settled']}")
