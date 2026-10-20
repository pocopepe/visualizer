#!/usr/bin/env python3
"""Figures for the corner audit (results/corner_audit, results/vco/factorial.csv) -> docs/figures/audit_*.png"""
import csv, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/figures"
NAVY, ORANGE, TEAL, GREY, RED, PURPLE, GREEN = "#1D2F82", "#E07A1F", "#2A9D8F", "#9AA0A6", "#C0392B", "#6A3D9A", "#2E8B57"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25, "figure.dpi": 150})
dev = {(r["corner"], int(r["temp_C"])): {k: float(v) for k, v in r.items() if k not in ("corner",)} for r in csv.DictReader(open(ROOT / "results/corner_audit/device_corners.csv"))}
F = {}
for r in csv.DictReader(open(ROOT / "results/vco/factorial.csv")):
    F[(r["corner"], int(r["temp_C"]), float(r["vctrl_V"]))] = float(r["freq_mhz"])
for r in csv.DictReader(open(ROOT / "results/vco/grid5corner.csv")):
    if r["freq_mhz"]:
        F[("pdk_" + r["corner"], int(float(r["temp_C"])), float(r["vctrl_V"]))] = float(r["freq_mhz"])
K = json.load(open(ROOT / "results/vco/kvco_fine/kvco_local.json"))
S = "stf"
NAME = {"s": "slow", "t": "typ", "f": "fast"}
nm = lambda n, p: f"n{n}p{p}"
tempco = lambda c: (F[(c, 85, 0.9)] - F[(c, -40, 0.9)]) / F[(c, 27, 0.9)] / 125 * 1e6
kv = lambda c: K[c[4:]]["k50"] if c.startswith("pdk_") else (F[(c, 27, 0.95)] - F[(c, 27, 0.85)]) / 0.1


def save(n):
    plt.tight_layout(); plt.savefig(OUT / f"{n}.png", dpi=200); plt.close()


# 1. device drive vs envelope
fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.9))
order = ["ss", "fs", "tt", "ff", "sf"]
for a, key, title in ((ax[0], "nmos_Id_0p9_uA", "NMOS Id at |Vgs| = 0.9 V (µA)"), (ax[1], "nmos_Id_1p8_uA", "NMOS Id at |Vgs| = 1.8 V (µA)")):
    vals = {c: dev[(c, 27)][key] for c in ["ss", "sf", "tt", "fs", "ff"]}
    lo, hi = vals["ss"], vals["ff"]
    a.axhspan(lo, hi, color=GREEN, alpha=0.12, label="ss–ff envelope")
    cols = {"ss": PURPLE, "sf": TEAL, "tt": NAVY, "fs": RED, "ff": ORANGE}
    a.bar(order, [vals[c] for c in order], color=[cols[c] for c in order])
    for i, c in enumerate(order):
        a.text(i, vals[c] * 1.01, f"{vals[c]:.1f}", ha="center", fontsize=9)
    a.set_ylim(min(vals.values()) * 0.8, max(vals.values()) * 1.1)
    a.set_title(title, fontsize=11)
ax[0].legend(fontsize=8, loc="upper left")
fig.suptitle("PDK skew corners vs the ss–ff envelope (27 °C): outside at the 0.9 V bias point", fontsize=11)
save("audit_device_envelope")

# 2. 3x3 maps
fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
mets = [("f at 0.9 V, 27 °C (MHz)", lambda c: F[(c, 27, 0.9)], "{:.0f}"), ("f at 1.4 V, 27 °C (MHz)", lambda c: F[(c, 27, 1.4)], "{:.0f}"),
        ("tempco at 0.9 V (ppm/°C)", tempco, "{:.0f}"), ("K_VCO/f at 0.9 V (1/V)", lambda c: kv(c) / F[(c, 27, 0.9)], "{:.2f}")]
for a, (t, fun, fm) in zip(axes, mets):
    M = [[fun(nm(n, p)) for p in S] for n in S]
    im = a.imshow(M, cmap="viridis_r" if "tempco" in t or "K_VCO" in t else "viridis", aspect="auto")
    for i in range(3):
        for j in range(3):
            a.text(j, i, fm.format(M[i][j]), ha="center", va="center", color="white", fontsize=11, fontweight="bold")
    a.set_xticks(range(3)); a.set_xticklabels([NAME[x] for x in S]); a.set_yticks(range(3)); a.set_yticklabels([NAME[x] for x in S])
    a.set_xlabel("PMOS corner"); a.set_title(t, fontsize=10); a.grid(False)
axes[0].set_ylabel("NMOS corner")
save("audit_factorial_maps")

# 3. tempco vs NMOS strength: factorial + PDK points
fig, ax = plt.subplots(figsize=(6.6, 4.2))
nid = {}
for c in ("ss", "tt", "ff", "sf", "fs"):
    nid[c] = dev[(c, 27)]["nmos_Id_0p9_uA"]
xs = {"s": nid["ss"], "t": nid["tt"], "f": nid["ff"]}
for p, col, mk in (("s", PURPLE, "v"), ("t", NAVY, "o"), ("f", ORANGE, "^")):
    ax.plot([xs[n] for n in S], [tempco(nm(n, p)) for n in S], marker=mk, color=col, label=f"PMOS {NAME[p]}", ms=7)
ax.scatter([nid["sf"]], [tempco("pdk_sf")], marker="*", s=220, color=TEAL, label="PDK sf", zorder=5)
ax.scatter([nid["fs"]], [tempco("pdk_fs")], marker="*", s=220, color=RED, label="PDK fs", zorder=5)
ax.set_xlabel("NMOS drive Id at |Vgs| = 0.9 V (µA), from ss / tt / ff"); ax.set_ylabel("tempco at V_ctrl = 0.9 V (ppm/°C)")
ax.set_title("Tempco falls with NMOS drive; PDK skews are the most extreme"); ax.legend(fontsize=8.5)
save("audit_tempco_vs_nmos")

# 4. tuning curves, 9 corners
fig, ax = plt.subplots(figsize=(7.4, 4.2))
V = [0.65, 0.7, 0.8, 0.9, 1.1, 1.25, 1.4]
cm = {"s": PURPLE, "t": NAVY, "f": ORANGE}
ls = {"s": ":", "t": "-", "f": "--"}
for n in S:
    for p in S:
        ax.plot(V, [F[(nm(n, p), 27, v)] for v in V], color=cm[n], ls=ls[p], marker="o", ms=3, lw=1.4, label=f"N {NAME[n]} / P {NAME[p]}")
ax.set_xlabel("V_ctrl (V)"); ax.set_ylabel("VCO frequency (MHz)")
ax.set_title("9 textbook corners: colour = NMOS, line style = PMOS (27 °C)")
ax.legend(fontsize=7, ncol=3, loc="upper left")
save("audit_tuning_9corners")
print("ok")
