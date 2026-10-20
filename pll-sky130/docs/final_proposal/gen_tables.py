#!/usr/bin/env python3
"""Generate LaTeX table fragments from results/final_numbers.md (no numbers retyped by hand)."""
import re
from pathlib import Path
here = Path(__file__).parent
txt = (here / "../../results/final_numbers.md").read_text()
def table(section):
    s = txt.split(section, 1)[1]
    rows = []
    for l in s.splitlines()[2:]:
        if not l.startswith("|"):
            if rows: break
            continue
        c = [x.strip() for x in l.strip("|").split("|")]
        if set(c[0]) <= set("-"): continue
        rows.append(c)
    return rows[0], rows[1:]
NAME = {"nsps": r"nsps (ss)", "nspt": "nspt", "nspf": "nspf", "ntps": "ntps", "ntpt": r"ntpt (tt)", "ntpf": "ntpf",
        "nfps": "nfps", "nfpt": "nfpt", "nfpf": r"nfpf (ff)", "pdk_sf": r"PDK sf (N fast, P slow)", "pdk_fs": r"PDK fs (N slow, P fast)"}
def sci(x):
    m, e = f"{float(x):.3e}".split("e"); return f"${m}\\times10^{{{int(e)}}}$"
def w(name, s): (here / name).write_text(s)
h, R = table("## Compensation on 11 corners")
# main
L = [r"\begin{tabular}{lrrrrrrl}\toprule", r"Corner & $f_0$ (MHz) & Base span (\%) & 2nd span (\%) & Max dev (\%) & Held-out (\%) & $C$ & $\pm0.3\,\%$ \\\midrule"]
for r in R:
    ok = "yes" if r[-1] == "yes" else r"\textbf{\textcolor{warn}{NO}}"
    L.append(f"{NAME[r[0]]} & {r[1]} & {r[2]} & {r[4]} & {r[5]} & {r[6]} & {r[7]} & {ok} \\\\")
L.append(r"\bottomrule\end{tabular}"); w("tab_comp_main.tex", "\n".join(L))
L = [r"\begin{tabular}{lrrrrrr}\toprule", r"Corner & 1st span (\%) & 2nd span (\%) & $k_1$ (V/$^\circ$C) & $k_2$ (V/$^\circ$C$^2$) & $f_0$ (MHz) & Base span (\%) \\\midrule"]
for r in R:
    L.append(f"{NAME[r[0]]} & {r[3]} & {r[4]} & {sci(r[8])} & {sci(r[9])} & {r[1]} & {r[2]} \\\\")
L.append(r"\bottomrule\end{tabular}"); w("tab_comp_coef.tex", "\n".join(L))
# closed loop
h, C = table("## Closed loop")
d = {r[0]: r for r in C}
L = [r"\begin{tabular}{lrrr}\toprule", r"Corner & $V_{lock}$ (V) & Coarse start (ns) & Cold start (ns) \\\midrule"]
for k in ["nsps", "nspt", "nspf", "ntps", "ntpt", "ntpf", "nfps", "nfpt", "nfpf", "pdk_sf", "pdk_fs"]:
    a, b = d[f"{k}_T27_coarse"], d[f"{k}_T27_cold"]
    L.append(f"{NAME[k]} & {float(a[4]):.3f} & {float(a[1]):.0f} & {float(b[1]):.0f} \\\\")
L.append(r"\bottomrule\end{tabular}"); w("tab_loop_main.tex", "\n".join(L))
L = [r"\begin{tabular}{lrrrrrr}\toprule", r"Case (corner, T, start) & Lock (ns) & $f_{VCO}$ (MHz) & $f$ err (\%) & $V_{lock}$ (V) & Ripple (mV) & Peak $V$ (V) \\\midrule"]
for r in C:
    m = re.match(r"(\w+?)_T(-?\d+)_(\w+)", r[0]); c, T, s = m.groups()
    nm = NAME[c].split(" (")[0].replace("_", " ") if c.startswith("n") else NAME[c].split(" (")[0]
    L.append(f"{nm}, {T} $^\\circ$C, {s} & {r[1]} & {r[2]} & {r[3]} & {r[4]} & {r[5]} & {r[6]} \\\\")
L.append(r"\bottomrule\end{tabular}"); w("tab_loop_all.tex", "\n".join(L))
# temperature rows
L = [r"\begin{tabular}{lrrr}\toprule", r"Corner & $-40\,^\circ$C & $27\,^\circ$C & $85\,^\circ$C \\\midrule"]
for k, nm in [("nsps", "ss"), ("ntpt", "tt"), ("nfpf", "ff")]:
    g = lambda T: float(d[f"{k}_T{T}_cold"][1])
    s85 = f"{g(85):.0f}" if k != "nsps" else r"\textbf{\textcolor{warn}{%.0f}}" % g(85)
    L.append(f"{nm} & {g(-40):.0f} & {g(27):.0f} & {s85} \\\\")
L.append(r"\bottomrule\end{tabular}"); w("tab_loop_temp.tex", "\n".join(L))
# device audit 27C
h, D = table("## Single-device audit")
L = [r"\begin{tabular}{lrrrrrr}\toprule", r"Corner & N $I_d$ 0.9 V ($\mu$A) & P $I_d$ 0.9 V ($\mu$A) & N $I_d$ 1.8 V ($\mu$A) & P $I_d$ 1.8 V ($\mu$A) & N $V_{th}$ (V) & P $|V_{th}|$ (V) \\\midrule"]
for r in D:
    if r[1] == "27": L.append(f"{r[0]} & {r[2]} & {r[3]} & {r[4]} & {r[5]} & {r[6]} & {r[7]} \\\\")
L.append(r"\bottomrule\end{tabular}"); w("tab_dev.tex", "\n".join(L))
