#!/usr/bin/env python3
"""Single-device audit of the sky130 process corners against textbook expectations.

For each corner x temperature, run DC Id-Vgs sweeps of the two core devices used in the VCO
(sky130_fd_pr__nfet_01v8 / pfet_01v8, W/L = 2/0.5) and extract
  - Id at |Vgs| = 0.9 V (the VCO bias region) and 1.8 V, saturation (|Vds| = 0.9 V / 1.8 V)
  - Vth (linear extrapolation at max gm, |Vds| = 50 mV)
Writes results/corner_audit/device_corners.csv; run `corner_audit.py --report` to print the checks.
"""
import csv
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results/corner_audit"
SPICE_MODELS = os.environ.get("SPICE_MODELS") or os.path.join(os.environ.get("PDK_ROOT", os.path.expanduser("~/pdk")), "volare/sky130/versions", os.environ.get("PDK_VERSION", "c6d73a35f524070e85faff4a6a9eef49553ebc2b"), os.environ.get("PDK", "sky130B"), "libs.tech/ngspice/sky130.lib.spice")
CORNERS = ["ss", "sf", "tt", "fs", "ff"]
TEMPS = [-40, 27, 85]
W, L = 2.0, 0.5

NET = """* device audit {corner} {temp} {vds_tag}
.lib "{models}" {corner}
.temp {temp}
Vdd vdd 0 1.8
Vgn gn 0 0
Bgp gp 0 V = 1.8 - V(gn)
Vdn dn 0 {vdsn}
Vdp dp 0 {vdsp}
Xn dn gn 0 0 sky130_fd_pr__nfet_01v8 l={L} w={W}
Xp dp gp vdd vdd sky130_fd_pr__pfet_01v8 l={L} w={W}
.control
set num_threads=1
dc Vgn 0 1.8 0.005
wrdata {out} i(Vdn) i(Vdp)
quit
.endc
.end
"""


def run(args):
    corner, temp, tag, vdsn, vdsp = args
    d = OUT / "raw"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{corner}_T{temp}_{tag}.txt"
    cir = d / f"{corner}_T{temp}_{tag}.cir"
    cir.write_text(NET.format(corner=corner, temp=temp, vds_tag=tag, models=SPICE_MODELS, vdsn=vdsn,
                              vdsp=vdsp, L=L, W=W, out=out))
    subprocess.run(["ngspice", "-b", str(cir)], stdin=subprocess.DEVNULL, capture_output=True, timeout=600)
    rows = [list(map(float, l.split())) for l in out.read_text().splitlines()]
    vg = [r[0] for r in rows]
    idn = [-r[1] for r in rows]   # current out of the n drain source is negative of drain current
    idp = [r[3] for r in rows]
    return (corner, temp, tag), vg, idn, idp


def interp(x, y, x0):
    for a, b, ya, yb in zip(x, x[1:], y, y[1:]):
        if a <= x0 <= b:
            return ya + (yb - ya) * (x0 - a) / (b - a)
    raise ValueError(x0)


def vth(vg, idv):
    gm = [(idv[i + 1] - idv[i - 1]) / (vg[i + 1] - vg[i - 1]) for i in range(1, len(vg) - 1)]
    k = max(range(len(gm)), key=gm.__getitem__) + 1
    return vg[k] - idv[k] / gm[k - 1]


def collect():
    jobs = [(c, t, "sat", "0.9", "0.9") for c in CORNERS for t in TEMPS]
    jobs += [(c, t, "lin", "0.05", "0.05") for c in CORNERS for t in TEMPS]
    res = {}
    with ThreadPoolExecutor(14) as ex:
        for key, vg, idn, idp in ex.map(run, jobs):
            res[key] = (vg, idn, idp)
    rows = []
    for c in CORNERS:
        for t in TEMPS:
            vg, idn, idp = res[(c, t, "sat")]
            vl, inl, ipl = res[(c, t, "lin")]
            # PMOS: gate = 1.8 - Vgn, so |Vsg| = Vgn; PMOS drain current is the same sweep variable
            rows.append({
                "corner": c, "temp_C": t,
                "nmos_Id_0p9_uA": interp(vg, idn, 0.9) * 1e6, "pmos_Id_0p9_uA": abs(interp(vg, idp, 0.9)) * 1e6,
                "nmos_Id_1p8_uA": interp(vg, idn, 1.8) * 1e6, "pmos_Id_1p8_uA": abs(interp(vg, idp, 1.8)) * 1e6,
                "nmos_Vth_V": vth(vl, inl), "pmos_Vth_V": vth(vl, [abs(x) for x in ipl]),
            })
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "device_corners.csv", "w", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys())
        w.writeheader()
        w.writerows({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows)
    return rows


if __name__ == "__main__":
    rows = collect()
    print("wrote", OUT / "device_corners.csv", len(rows), "rows")
