#!/usr/bin/env python3
"""Parse results/vco/factorial/run.log (+ the PDK grid) into CSV and run the textbook-ordering checks."""
import csv, re, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
rows = []
for l in (ROOT / "results/vco/factorial/run.log").read_text().splitlines():
    m = re.match(r"\[(\w+)_T(-?\d+)_Vc([\d.]+)\] exit=0.*f_osc = ([\d.]+) MHz", l)
    if m:
        rows.append((m[1], int(m[2]), float(m[3]), float(m[4])))
with open(ROOT / "results/vco/factorial.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["corner", "temp_C", "vctrl_V", "freq_mhz"]); w.writerows(rows)
F = {(c, t, v): f for c, t, v, f in rows}
# merge PDK-native corners so ss/tt/ff (== nsps/ntpt/nfpf) and the sky130 skew corners can be compared
for r in csv.DictReader(open(ROOT / "results/vco/grid5corner.csv")):
    if r["freq_mhz"]:
        F[("pdk_" + r["corner"], int(float(r["temp_C"])), float(r["vctrl_V"]))] = float(r["freq_mhz"])
for n in "stf":
    pass
S = "stf"
def name(n, p): return f"n{n}p{p}"
def tempco(c): return (F[(c, 85, 0.9)] - F[(c, -40, 0.9)]) / F[(c, 27, 0.9)] / 125 * 1e6
KLOC = json.load(open(ROOT / "results/vco/kvco_fine/kvco_local.json"))
def kv(c):
    if c.startswith("pdk_"):
        return KLOC[c[4:]]["k50"]
    return (F[(c, 27, 0.95)] - F[(c, 27, 0.85)]) / 0.1
def mat(fun, fmt):
    print("          PMOS: slow  typ   fast")
    for n in S:
        print(f"NMOS {dict(s='slow',t='typ ',f='fast')[n]}  " + "  ".join(fmt(fun(name(n, p))) for p in S))
out = {}
for label, fun, fmt in [("f(0.9 V, 27C) MHz", lambda c: F[(c, 27, 0.9)], "{:6.1f}".format),
                         ("f(1.4 V, 27C) MHz", lambda c: F[(c, 27, 1.4)], "{:6.1f}".format),
                         ("tempco ppm/C @0.9V", tempco, "{:6.0f}".format),
                         ("K_VCO MHz/V @0.9V", kv, "{:6.0f}".format),
                         ("K_VCO/f  1/V @0.9V", lambda c: kv(c) / F[(c, 27, 0.9)], "{:6.2f}".format)]:
    print("\n" + label); mat(fun, fmt)
    out[label] = {name(n, p): fun(name(n, p)) for n in S for p in S}
print("\nPDK-native skew corners for comparison (same metrics):")
for c in ("pdk_sf", "pdk_fs"):
    print(c, "f0.9=%.1f f1.4=%.1f tempco=%.0f K=%.0f" % (F[(c, 27, 0.9)], F[(c, 27, 1.4)], tempco(c), kv(c)))
# checks
def mono(vals): return all(a <= b for a, b in zip(vals, vals[1:]))
res = []
for label in ("f(0.9 V, 27C) MHz", "f(1.4 V, 27C) MHz"):
    d = out[label]
    res.append((label + ": increases with NMOS strength (each PMOS state)", all(mono([d[name(n, p)] for n in S]) for p in S)))
    res.append((label + ": increases with PMOS strength (each NMOS state)", all(mono([d[name(n, p)] for p in S]) for n in S)))
    res.append((label + ": nsps is the minimum, nfpf the maximum of the 9", min(d, key=d.get) == "nsps" and max(d, key=d.get) == "nfpf"))
d = out["tempco ppm/C @0.9V"]
res.append(("tempco decreases with NMOS strength (each PMOS state)", all(mono([-d[name(n, p)] for n in S]) for p in S)))
res.append(("tempco: nfpf < ntpt < nsps", d["nfpf"] < d["ntpt"] < d["nsps"]))
for label in ("f(0.9 V, 27C) MHz", "f(1.4 V, 27C) MHz"):
    lo, hi = F[("nsps", 27, 0.9 if "0.9" in label else 1.4)], F[("nfpf", 27, 0.9 if "0.9" in label else 1.4)]
    for c in ("pdk_sf", "pdk_fs"):
        v = F[(c, 27, 0.9 if "0.9" in label else 1.4)]
        res.append((f"{label}: PDK {c[4:]} inside [ss, ff] envelope", lo <= v <= hi))
for c in ("pdk_sf", "pdk_fs"):
    t = tempco(c)
    res.append((f"tempco: PDK {c[4:]} ({t:.0f}) inside [ff, ss] = [{tempco('nfpf'):.0f}, {tempco('nsps'):.0f}]", tempco("nfpf") <= t <= tempco("nsps")))
print()
for k, v in res: print("PASS" if v else "FAIL", "-", k)
json.dump({"tables": out, "checks": [[k, bool(v)] for k, v in res]}, open(ROOT / "results/corner_audit/factorial_summary.json", "w"), indent=1)
