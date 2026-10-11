#!/usr/bin/env python3
"""Render the Review-2 figures (PNG) from results/figdata.json into docs/figures/."""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from stats import ci95  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/figures"
OUT.mkdir(parents=True, exist_ok=True)
D = json.loads((ROOT / "results/figdata.json").read_text())

NAVY, ORANGE, TEAL, GREY, RED = "#1D2F82", "#E07A1F", "#2A9D8F", "#9AA0A6", "#C0392B"
CC = {"ss": "#6A3D9A", "sf": "#2A9D8F", "tt": NAVY, "fs": RED, "ff": ORANGE}
ORDER = ["sf", "ff", "tt", "ss", "fs"]
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 150})


def save(name):
    plt.tight_layout()
    plt.savefig(OUT / f"{name}.png", dpi=200)
    plt.close()


def temps(d):
    ks = sorted(d, key=int)
    return [int(k) for k in ks], [d[k] for k in ks]


# 1. tuning curves
plt.figure(figsize=(7, 4))
for c in ORDER:
    x, y = zip(*D["tuning"][c])
    plt.plot(x, y, "o-", color=CC[c], label=c, ms=4)
plt.axvline(0.9, ls="--", color=GREY)
plt.text(0.91, 415, "design point 0.9 V", color="#555", fontsize=9)
plt.axvspan(0.5, 0.65, color=RED, alpha=0.07)
plt.text(0.505, 330, "f < 18 MHz\nbelow 0.65 V\n(still oscillates)", color=RED, fontsize=9)
plt.xlim(0.5, 1.45)
plt.xlabel("Control voltage V_ctrl (V)"); plt.ylabel("VCO frequency (MHz)")
plt.title("VCO tuning curve, 27 °C, all 5 process corners")
plt.legend(title="corner", ncol=5, fontsize=9, loc="lower right")
save("tuning")

# 2. uncompensated drift vs T
plt.figure(figsize=(7, 4))
plt.axhspan(-0.3, 0.3, color="green", alpha=0.12, label="±0.3 % spec")
for c in ORDER:
    x, y = temps(D["temp_dev"][c])
    plt.plot(x, y, "o-", color=CC[c], label=f"{c}  ({D['tempco_ppm'][c]:.0f} ppm/°C)", ms=4)
plt.xlabel("Temperature (°C)"); plt.ylabel("Frequency change vs 27 °C (%)")
plt.title("Uncompensated drift at V_ctrl = 0.9 V")
plt.legend(fontsize=9)
save("drift_uncomp")

# 3. tempco bar
plt.figure(figsize=(6, 3.6))
vals = [D["tempco_ppm"][c] for c in ORDER]
bars = plt.bar(ORDER, vals, color=[CC[c] for c in ORDER])
for b, v in zip(bars, vals):
    plt.text(b.get_x() + b.get_width() / 2, v + 25, f"{v:.0f}", ha="center", fontsize=10)
plt.ylabel("Average tempco (ppm/°C)")
plt.title("12.5× spread across corners (sf 112 → fs 1399)")
save("tempco_bar")

# 4. tt local tempco
plt.figure(figsize=(6, 3.4))
lab, v = zip(*D["tt_local_tempco"])
plt.bar([l.replace(" to ", "→") for l in lab], v, color=NAVY)
plt.axhline(D["tempco_ppm"]["tt"], ls="--", color=ORANGE, label=f"single-number average {D['tempco_ppm']['tt']:.0f}")
plt.ylabel("Local tempco (ppm/°C)"); plt.xlabel("Temperature interval (°C)")
plt.title("tt corner: the drift is curved, not a straight line")
plt.legend(fontsize=9)
save("tt_local")

# 5. compensation at tt
c = D["comp"]["tt"]
plt.figure(figsize=(7, 4.2))
plt.axhspan(-0.3, 0.3, color="green", alpha=0.12, label="±0.3 % spec")
for key, col, lab_, st in [("base_dev", GREY, "uncompensated", "o-"), ("first_dev", TEAL, "1st-order", "s-"),
                           ("second_dev", NAVY, "2nd-order (refined)", "D-")]:
    x, y = temps(c[key]); plt.plot(x, y, st, color=col, label=lab_, ms=5)
x, y = temps(D["tt_naive_dev"]); plt.plot(x, y, "x--", color=RED, label="2nd-order, naive coefficients", ms=6)
x, y = temps(c["holdout_dev"]); plt.plot(x, y, "*", color=ORANGE, ms=12, label="held-out temps (never fitted)")
plt.xlabel("Temperature (°C)"); plt.ylabel("Frequency change vs 27 °C (%)")
plt.title("Compensation at the typical (tt) corner")
plt.legend(fontsize=8.5, loc="lower left")
save("comp_tt")

# 6. max |dev| per corner, log scale
plt.figure(figsize=(7.2, 4))
w = 0.26
xs = range(len(ORDER))
for i, (key, col, lab_) in enumerate([("base_dev", GREY, "uncompensated"), ("first_dev", TEAL, "1st-order"),
                                      ("second_dev", NAVY, "2nd-order")]):
    vals = [max(abs(v) for v in D["comp"][cn][key].values()) for cn in ORDER]
    plt.bar([x + (i - 1) * w for x in xs], vals, w, color=col, label=lab_)
    if key == "second_dev":
        for x, v in zip(xs, vals):
            plt.text(x + w, v * 1.15, f"{v:.2f}%", ha="center", fontsize=8.5, color=NAVY)
plt.axhline(0.3, ls="--", color="green", lw=2, label="±0.3 % spec")
plt.yscale("log"); plt.xticks(list(xs), ORDER)
plt.ylabel("Max |frequency deviation| (%), log scale")
plt.title("After 2nd-order compensation: spec met at sf and ff only")
plt.legend(fontsize=9, ncol=2)
save("comp_corners")

# 7. MC paired scatter
m = D["mc_absdrift"]
seeds = sorted(set(m["first"]) & set(m["second"]), key=int)
f1 = [m["first"][s] for s in seeds]; f2 = [m["second"][s] for s in seeds]
wins = sum(b < a for a, b in zip(f1, f2))
plt.figure(figsize=(5.2, 5))
lim = max(f1 + f2) * 1.08
plt.fill_between([0, lim], [0, 0], [0, lim], color="green", alpha=0.07)
plt.plot([0, lim], [0, lim], "--", color=GREY)
plt.scatter(f1, f2, color=NAVY, s=36, zorder=3)
plt.text(lim * 0.55, lim * 0.12, f"2nd-order better\n({wins}/{len(seeds)} mismatch samples)", color="green", fontsize=10)
plt.xlim(0, lim); plt.ylim(0, lim)
plt.xlabel("1st-order |drift| (MHz)"); plt.ylabel("2nd-order |drift| (MHz)")
plt.title("Monte Carlo, same mismatch sample\nthrough both networks (n = 30)")
save("mc_paired")

# 8. MC means with CI
plt.figure(figsize=(6, 3.8))
arms = [("baseline", "uncompensated", GREY), ("first", "1st-order", TEAL), ("second", "2nd-order", NAVY)]
for i, (k, lab_, col) in enumerate(arms):
    vals = list(m[k].values())
    mu, hw = ci95(vals)
    plt.bar(i, mu, color=col, yerr=hw, capsize=8)
    plt.text(i, mu + hw + 0.5, f"{mu:.2f} MHz\n(n={len(vals)})", ha="center", fontsize=9)
plt.xticks(range(3), [a[1] for a in arms])
plt.ylabel("Mean |drift|, 85 °C vs −40 °C (MHz)")
plt.title("Monte Carlo means with 95 % confidence intervals")
plt.ylim(0, 25)
save("mc_means")

# 9. lock transients
plt.figure(figsize=(7.4, 4))
for key, lab_, col, tl in [("lock_coarse", "start at 0.85 V (coarse-tuned)", TEAL, 577),
                           ("lock_cold", "true cold start from 0 V (boosted CP)", NAVY, 839)]:
    t, v = zip(*D[key]); plt.plot(t, v, color=col, lw=1.4, label=f"{lab_}: lock {tl} ns")
    plt.axvline(tl, ls=":", color=col)
plt.axhspan(0.9 * 0.98, 0.9 * 1.02, color="green", alpha=0.12, label="±2 % lock band")
plt.axhline(0.65, ls="--", color=RED, lw=1); plt.text(1250, 0.57, "below 0.65 V the VCO is < 18 MHz", color=RED, fontsize=9)
plt.xlabel("Time (ns)"); plt.ylabel("V_ctrl (V)")
plt.title("Closed-loop lock (tt, 27 °C); spec < 2000 ns")
plt.legend(fontsize=8.5, loc="lower right")
save("lock")

# 10. alpha sweep
plt.figure(figsize=(5.6, 3.6))
a, cc = zip(*D["alpha_C"])
plt.plot(a, cc, "o-", color=NAVY)
plt.xlabel("Compensation strength α (1 = fitted)"); plt.ylabel("Compensation ratio C")
plt.title("Strength sweep: C values ready for the H1 test")
save("alpha")

print("figures ->", OUT, sorted(p.name for p in OUT.glob("*.png")))
