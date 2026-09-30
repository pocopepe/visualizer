#!/usr/bin/env python3
"""Collect every number the Review-2 figures plot into results/figdata.json.
Reads the raw ngspice dumps (gitignored, regenerate with the sweep scripts)."""
import csv
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_freq import load_columns, rising_crossings  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORNERS = ["ss", "sf", "tt", "fs", "ff"]
TEMPS = [-40, -20, 0, 27, 50, 85]


def freq(path, skip=0.3):
    t, v = load_columns(path)
    s = skip * t[-1]
    t2 = [a for a in t if a >= s]
    v2 = [b for a, b in zip(t, v) if a >= s]
    c = rising_crossings(t2, v2, 0.9)
    if len(c) < 3:
        return None
    p = [c[i + 1] - c[i] for i in range(len(c) - 1)]
    return 1 / (sum(p) / len(p)) / 1e6


def one(pattern):
    hits = glob.glob(str(ROOT / pattern))
    assert len(hits) == 1, (pattern, hits)
    return freq(hits[0])


def dev_pct(fs):
    f27 = fs["27"]
    return {k: (v - f27) / f27 * 100 for k, v in fs.items()}


def main():
    out = {}
    rows = list(csv.DictReader(open(ROOT / "results/vco/grid5corner.csv")))
    out["tuning"] = {c: sorted([(float(r["vctrl_V"]), float(r["freq_mhz"])) for r in rows
                                if r["corner"] == c and r["temp_C"] == "27.0" and r["freq_mhz"]])
                     for c in CORNERS}
    temp = {}
    for c in CORNERS:
        temp[c] = {str(int(float(r["temp_C"]))): float(r["freq_mhz"]) for r in rows
                   if r["corner"] == c and abs(float(r["vctrl_V"]) - 0.9) < 1e-6 and r["freq_mhz"]}
    out["temp_f"] = temp
    out["temp_dev"] = {c: dev_pct(temp[c]) for c in CORNERS}
    out["tempco_ppm"] = {c: (temp[c]["85"] - temp[c]["-40"]) / temp[c]["27"] / 125 * 1e6 for c in CORNERS}
    tt = temp["tt"]
    out["tt_local_tempco"] = [(f"{a} to {b}", (tt[str(b)] - tt[str(a)]) / tt["27"] / (b - a) * 1e6)
                              for a, b in zip(TEMPS, TEMPS[1:])]

    comp = {}
    for c in CORNERS:
        first = {str(T): one(f"results/comp/percorner_1st/{c}_T{T}_Vc0.9_k1*_k20.txt") for T in TEMPS}
        second = {str(T): one(f"results/comp/percorner_2nd/{c}_T{T}_Vc0.9_*.txt") for T in TEMPS}
        hold = {str(T): one(f"results/comp/holdout/{c}_T{T}_Vc0.9_*.txt") for T in (-30, 10, 40, 70)}
        f27 = second["27"]
        comp[c] = {
            "base_dev": out["temp_dev"][c],
            "first_dev": dev_pct(first),
            "second_dev": dev_pct(second),
            "holdout_dev": {k: (v - f27) / f27 * 100 for k, v in hold.items()},
            "span": [(max(d.values()) - min(d.values())) / d["27"] * 100 for d in (temp[c], first, second)],
            "maxdev_2nd": max(abs(v) for v in dev_pct(second).values()),
        }
    out["comp"] = comp
    naive = {str(T): one(f"results/comp/phase1/tt_T{T}_Vc0.9_k1-2.163e-4_k21.299e-6.txt") for T in TEMPS}
    out["tt_naive_dev"] = dev_pct(naive)

    pat = re.compile(r"tt_T(-?\d+)_k1([^_]+)_k2([^_]+)_seed(\d+)\.txt$")
    arms = {("0", "0"): "baseline", ("-2.163e-4", "0"): "first",
            ("-1.321953e-4", "2.893555e-7"): "second"}
    mc = {}
    for f in glob.glob(str(ROOT / "results/mc/*.txt")):
        m = pat.search(f)
        arm = arms.get((m[2], m[3])) if m else None
        if arm:
            mc.setdefault(arm, {}).setdefault(int(m[4]), {})[int(m[1])] = freq(f)
    out["mc_absdrift"] = {arm: {s: abs(d[85] - d[-40]) for s, d in sorted(v.items())
                                if d.get(85) and d.get(-40)} for arm, v in mc.items()}

    def trace(path, stride):
        pts = []
        with open(path) as fh:
            for i, line in enumerate(fh):
                if i % stride == 0:
                    p = line.split()
                    pts.append((float(p[0]) * 1e9, float(p[1])))
        return pts
    out["lock_coarse"] = trace(ROOT / "results/loop/run4_icfix.txt", 250)
    out["lock_cold"] = trace(ROOT / "blocks/top/results_loop_coldstart.txt", 375)

    base_span = out["comp"]["tt"]["span"][0]
    alpha = [(0.0, 1.0)]
    for a in (0.25, 0.5, 0.75, 1.25):
        fs = {str(T): None for T in TEMPS}
        for T in TEMPS:
            hits = [h for h in glob.glob(str(ROOT / f"results/comp/alpha/tt_T{T}_Vc0.9_*.txt"))]
            # alpha files are distinguished by k1 = alpha * k1_full(tt refined)
            k1 = a * -1.320197e-4
            hit = [h for h in hits if abs(float(re.search(r"_k1([^_]+)_k2", h)[1]) - k1) < 1e-9]
            fs[str(T)] = freq(hit[0])
        alpha.append((a, base_span / ((max(fs.values()) - min(fs.values())) / fs["27"] * 100)))
    alpha.append((1.0, base_span / out["comp"]["tt"]["span"][2]))
    out["alpha_C"] = sorted(alpha)

    (ROOT / "results/figdata.json").write_text(json.dumps(out, indent=1))
    print("wrote results/figdata.json")


if __name__ == "__main__":
    main()
