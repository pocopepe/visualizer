#!/usr/bin/env python3
"""Final-review figures: compensation on 11 corners, Monte Carlo (n=72), closed-loop campaign -> docs/figures/final_*.png"""
import csv, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_mc as A  # noqa: E402
from stats import ci95  # noqa: E402

OUT = ROOT / "docs/figures"
NAVY, ORANGE, TEAL, GREY, RED, PURPLE, GREEN = "#1D2F82", "#E07A1F", "#2A9D8F", "#9AA0A6", "#C0392B", "#6A3D9A", "#2E8B57"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 150})
ORDER = ["nsps", "nspt", "nspf", "ntps", "ntpt", "ntpf", "nfps", "nfpt", "nfpf", "pdk_sf", "pdk_fs"]
LAB = {c: c.replace("n", "N").replace("p", "/P ").replace("N", "N ", 1) if not c.startswith("pdk") else "PDK " + c[4:] for c in ORDER}
LAB = {"nsps": "N slow\nP slow (ss)", "nspt": "N slow\nP typ", "nspf": "N slow\nP fast", "ntps": "N typ\nP slow", "ntpt": "N typ\nP typ (tt)",
       "ntpf": "N typ\nP fast", "nfps": "N fast\nP slow", "nfpt": "N fast\nP typ", "nfpf": "N fast\nP fast (ff)", "pdk_sf": "PDK sf\n(fast N,slow P)", "pdk_fs": "PDK fs\n(slow N,fast P)"}
COL = {c: (GREEN if c in ("nsps", "ntpt", "nfpf") else NAVY) for c in ORDER}
COL.update({"pdk_sf": TEAL, "pdk_fs": RED})
comp = {r["corner"]: r for r in json.load(open(ROOT / "results/comp/factorial/factorial_comp_all.json"))}
camp = {r["case"]: r for r in csv.DictReader(open(ROOT / "results/loop/campaign/summary.csv"))}


def save(n):
    plt.tight_layout(); plt.savefig(OUT / f"final_{n}.png", dpi=200); plt.close()


# 1. compensation on 11 corners
fig, ax = plt.subplots(figsize=(11, 4.2))
w = 0.27; x = np.arange(len(ORDER))
for i, (key, col, lab) in enumerate([("baseline", GREY, "uncompensated"), ("order1", TEAL, "1st order"), ("order2", NAVY, "2nd order")]):
    v = [comp[c][key]["maxdev_pct"] for c in ORDER]
    ax.bar(x + (i - 1) * w, v, w, color=col, label=lab)
    if key == "order2":
        for xi, vi in zip(x, v):
            ax.text(xi + w, vi * 1.15, f"{vi:.2f}", ha="center", fontsize=8, color=NAVY)
ax.axhline(0.3, ls="--", color=GREEN, lw=2, label="±0.3 % spec")
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels([LAB[c] for c in ORDER], fontsize=8)
ax.set_ylabel("max |f deviation| vs 27 °C (%), log"); ax.set_title("Compensation fitted on the measured f(T, V) surface: 8 of 11 corners meet ±0.3 % (nominal, no mismatch)")
ax.legend(fontsize=9, ncol=4); save("comp_corners")

# 2. tt compensation curves
F = {}
for r in csv.DictReader(open(ROOT / "results/vco/factorial.csv")):
    F[(r["corner"], int(r["temp_C"]), float(r["vctrl_V"]))] = float(r["freq_mhz"])
T6 = [-40, -20, 0, 27, 50, 85]
r = comp["ntpt"]; f27 = r["f27_MHz"]
fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.axhspan(-0.3, 0.3, color=GREEN, alpha=0.12, label="±0.3 % spec")
ax.plot(T6, [(F[("ntpt", t, 0.9)] - f27) / f27 * 100 for t in T6], "o-", color=GREY, label="uncompensated")
ax.plot(T6, [(r["order1"]["f"][str(t)] - f27) / f27 * 100 for t in T6], "s-", color=TEAL, label=f"1st order (k1 = {r['order1']['k1']*1e4:.2f}e-4 V/°C)")
ax.plot(T6, [(r["order2"]["f"][str(t)] - f27) / f27 * 100 for t in T6], "D-", color=NAVY, label="2nd order")
ax.plot([int(k) for k in r["holdout"]["dev_pct"]], list(r["holdout"]["dev_pct"].values()), "*", color=ORANGE, ms=13, label="held-out temperatures")
ax.set_xlabel("Temperature (°C)"); ax.set_ylabel("Δf vs 27 °C (%)"); ax.set_title("Typical corner, corrected coefficients"); ax.legend(fontsize=8.5); save("comp_tt")

# 3. Monte Carlo n=72
A.ARMS = A.ARMS_V2
d = A.load("results/mc_v2", ("results/mc",))
seeds = sorted(s for (a, s) in d if a == "1st_order" and ("2nd_order_refined", s) in d)
f1 = [abs(d[("1st_order", s)]) for s in seeds]; f2 = [abs(d[("2nd_order_refined", s)]) for s in seeds]
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1, 1.1]})
lim = max(f1 + f2) * 1.08
ax[0].plot([0, lim], [0, lim], "--", color=GREY); ax[0].scatter(f1, f2, color=NAVY, s=22)
wins = sum(b < a for a, b in zip(f1, f2))
ax[0].text(lim * 0.5, lim * 0.08, f"2nd order smaller in {wins}/{len(seeds)} chips", fontsize=9, color=GREEN)
ax[0].set_xlim(0, lim); ax[0].set_ylim(0, lim); ax[0].set_xlabel("1st-order |drift| (MHz)"); ax[0].set_ylabel("2nd-order |drift| (MHz)")
ax[0].set_title(f"Same mismatch sample through both networks (n = {len(seeds)})", fontsize=10)
vals = {}
for i, (k, lab, col) in enumerate([("baseline", "uncompensated", GREY), ("1st_order", "1st order", TEAL), ("2nd_order_refined", "2nd order", NAVY)]):
    v = [abs(d[(k, s)]) for s in seeds]; mu, hw = ci95(v); vals[k] = v
    ax[1].bar(i, mu, color=col, yerr=hw, capsize=8); ax[1].text(i, mu + hw + 0.4, f"{mu:.2f} MHz", ha="center", fontsize=9)
ax[1].set_xticks(range(3)); ax[1].set_xticklabels(["uncompensated", "1st order", "2nd order"]); ax[1].set_ylim(0, 26)
ax[1].set_ylabel("mean |drift|, 85 vs −40 °C (MHz)"); ax[1].set_title("Means with 95 % CI (mismatch floor ≈ 3 MHz ≈ 1.2–1.4 %)", fontsize=10)
save("mc")

# 4. closed-loop lock per corner (27 C)
fig, ax = plt.subplots(figsize=(11, 4.2))
x = np.arange(len(ORDER))
co = [float(camp[f"{'pdk_' if c.startswith('pdk') else ''}{c.replace('pdk_', '')}_T27_coarse"]["lock_ns"]) for c in ORDER]
cd = [float(camp[f"{'pdk_' if c.startswith('pdk') else ''}{c.replace('pdk_', '')}_T27_cold"]["lock_ns"]) for c in ORDER]
ax.bar(x - 0.2, co, 0.4, color=TEAL, label="coarse start (0.85 V)"); ax.bar(x + 0.2, cd, 0.4, color=NAVY, label="cold start (0 V, boosted CP)")
for xi, a, b in zip(x, co, cd):
    ax.text(xi - 0.2, a + 25, f"{a:.0f}", ha="center", fontsize=7.5); ax.text(xi + 0.2, b + 25, f"{b:.0f}", ha="center", fontsize=7.5)
ax.axhline(2000, ls="--", color=RED); ax.text(len(ORDER) - 0.6, 2040, "spec 2000 ns", color=RED, ha="right", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([LAB[c] for c in ORDER], fontsize=8); ax.set_ylim(0, 2300); ax.set_ylabel("lock time (ns), 27 °C")
ax.set_title("Closed loop (R2 = 3.6 kΩ) locks at all 11 corners; f_VCO = 226.17 MHz = 8 × f_ref in every run"); ax.legend(fontsize=9, loc="upper left"); save("lock_corners")

# 5. lock vs temperature (cold start) + lock voltage vs T
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
for c, col, lab in (("nsps", PURPLE, "ss"), ("ntpt", NAVY, "tt"), ("nfpf", ORANGE, "ff")):
    Ts = [-40, 27, 85]
    lk = [float(camp[f"{c}_T{t}_cold"]["lock_ns"]) for t in Ts]; vl = [float(camp[f"{c}_T{t}_cold"]["vctrl_final_V"]) for t in Ts]
    ax[0].plot(Ts, lk, "o-", color=col, label=lab); ax[1].plot(Ts, [(v - vl[1]) * 1e3 for v in vl], "o-", color=col, label=lab)
ax[0].axhline(2000, ls="--", color=RED); ax[0].text(-38, 2030, "spec 2000 ns", color=RED, fontsize=9)
ax[0].set_xlabel("Temperature (°C)"); ax[0].set_ylabel("cold-start lock time (ns)"); ax[0].set_ylim(1000, 2300); ax[0].legend(fontsize=9); ax[0].set_title("ss at 85 °C misses the spec by 4 %", fontsize=10)
ax[1].set_xlabel("Temperature (°C)"); ax[1].set_ylabel("lock V_ctrl minus its 27 °C value (mV)"); ax[1].set_title("The loop absorbs the VCO's temperature drift", fontsize=10); ax[1].legend(fontsize=9)
save("lock_temp")

# 6. closed-loop vs open-loop lock voltage
Vopen = {}
FA = dict(F)
for r_ in csv.DictReader(open(ROOT / "results/vco/grid5corner.csv")):
    if r_["freq_mhz"]:
        FA[("pdk_" + r_["corner"], int(float(r_["temp_C"])), float(r_["vctrl_V"]))] = float(r_["freq_mhz"])
import glob, re, subprocess
for fpath in glob.glob(str(ROOT / "results/vco/kvco_fine/*.txt")):
    m = re.search(r"(\w+)_T27_Vc([\d.]+)\.txt", fpath); o = subprocess.run([sys.executable, str(ROOT / "scripts/extract_freq.py"), fpath], capture_output=True, text=True).stdout
    FA[("pdk_" + m[1], 27, float(m[2]))] = float(re.search(r"f_osc = ([\d.]+)", o)[1])
xs, ys = [], []
for c in ORDER:
    pts = sorted((v, f) for (cc, t, v), f in FA.items() if cc == c and t == 27 and 0.8 <= v <= 1.1)
    near = sorted(pts, key=lambda p: abs(p[1] - 226.2))[:4]
    cf = np.polyfit([p[0] for p in near], [p[1] for p in near], 2); cf[2] -= 226.2
    rt = [z.real for z in np.roots(cf) if abs(z.imag) < 1e-9 and 0.8 < z.real < 1.1]; xs.append(min(rt, key=lambda z: abs(z - 0.9)))
    ys.append(float(camp[f"{'pdk_' if c.startswith('pdk') else ''}{c.replace('pdk_', '')}_T27_coarse"]["vctrl_final_V"]))
fig, ax = plt.subplots(figsize=(4.8, 4.6))
ax.plot([0.84, 0.98], [0.84, 0.98], "--", color=GREY); ax.scatter(xs, ys, color=NAVY, s=40)
ax.set_xlabel("open-loop V_ctrl for 226.2 MHz (V)"); ax.set_ylabel("closed-loop lock V_ctrl (V)")
ax.set_title(f"Independent check, 11 corners:\nmax difference {max(abs(a-b) for a,b in zip(xs,ys))*1e3:.1f} mV", fontsize=10); save("vlock_check")

# 7. cold-start traces for three corners
fig, ax = plt.subplots(figsize=(7.4, 4))
for c, col, lab in (("nsps", PURPLE, "ss"), ("ntpt", NAVY, "tt"), ("nfpf", ORANGE, "ff")):
    a = np.loadtxt(ROOT / f"results/loop/campaign/{c}_T27_cold.txt", usecols=(0, 1)); k = max(1, len(a) // 600)
    ax.plot(a[::k, 0] * 1e9, a[::k, 1], color=col, lw=1.3, label=f"{lab}: lock {float(camp[c + '_T27_cold']['lock_ns']):.0f} ns")
ax.axhspan(0.88, 0.92, color="none"); ax.set_xlim(0, 3000); ax.set_xlabel("Time (ns)"); ax.set_ylabel("V_ctrl (V)"); ax.set_title("0 V cold start at the three symmetric corners (27 °C)")
ax.legend(fontsize=9, loc="lower right"); save("cold_traces")
print("ok", sorted(p.name for p in OUT.glob("final_*.png")))
