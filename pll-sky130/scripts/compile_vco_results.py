#!/usr/bin/env python3
"""Aggregate a batch of extract_freq.py results into CSV + summary stats.

Post-critique rev2: adds supply-current parsing from the ngspice .meas log
output, flags low-confidence (few-period) points instead of silently
including them in fits, and replaces two-point secant K_VCO/tempco numbers
with proper fits (the baseline curve is visibly nonlinear -- see charter
critique item 5: a scalar secant hides up to ~3x local-slope variation and
would contaminate the compensation-ratio C measurement later).
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEAS_RE = re.compile(r"^\s*i_avg_a\s*=\s*([\d.eE+-]+)", re.IGNORECASE)


def run_extract(txt_path):
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts/extract_freq.py"), str(txt_path), "--json"],
        capture_output=True, text=True,
    )
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"file": str(txt_path), "error": "parse_failed", "raw": out.stdout}


def parse_supply_current(log_path):
    if not log_path.exists():
        return None
    for line in log_path.read_text(errors="replace").splitlines():
        m = MEAS_RE.match(line)
        if m:
            return float(m.group(1))
    return None


def poly_fit(xs, ys, degree):
    """Least-squares polynomial fit without numpy (small point counts)."""
    n = degree + 1
    # Build normal equations A^T A c = A^T y
    A = [[x ** p for p in range(n)] for x in xs]
    ATA = [[sum(A[k][i] * A[k][j] for k in range(len(xs))) for j in range(n)] for i in range(n)]
    ATy = [sum(A[k][i] * ys[k] for k in range(len(xs))) for i in range(n)]
    # Gaussian elimination
    M = [row[:] + [ATy[i]] for i, row in enumerate(ATA)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        if abs(pv) < 1e-30:
            continue
        M[col] = [v / pv for v in M[col]]
        for r in range(n):
            if r != col:
                factor = M[r][col]
                M[r] = [M[r][i] - factor * M[col][i] for i in range(n + 1)]
    return [M[i][n] for i in range(n)]


def poly_eval(coeffs, x):
    return sum(c * x ** p for p, c in enumerate(coeffs))


def poly_deriv_eval(coeffs, x):
    return sum(p * c * x ** (p - 1) for p, c in enumerate(coeffs) if p >= 1)


def main(sweep_dir, csv_out):
    sweep_dir = Path(sweep_dir)
    rows = []
    for txt in sorted(sweep_dir.glob("*.txt")):
        tag = txt.stem  # e.g. tt_T27_Vc0.9
        parts = tag.split("_")
        corner = parts[0]
        temp = parts[1][1:]
        vctrl = parts[2][2:]
        r = run_extract(txt)
        r["corner"] = corner
        r["temp_C"] = float(temp)
        r["vctrl_V"] = float(vctrl)
        r["i_avg_A"] = parse_supply_current(sweep_dir / f"{tag}.log")
        rows.append(r)

    fields = ["corner", "temp_C", "vctrl_V", "freq_mhz", "n_periods", "low_confidence",
              "period_regularity_frac", "v_min_steady", "v_max_steady", "i_avg_A", "error"]
    with open(csv_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {csv_out}")

    ok = lambda r: "freq_mhz" in r  # noqa: E731
    high_conf = lambda r: ok(r) and not r.get("low_confidence", False)  # noqa: E731

    # K_VCO: points at fixed nominal temp, varying vctrl (tt corner only --
    # ss/ff points at T=27 exist too, for the corner-shape check below, and
    # must not leak into the single-corner tuning curve)
    kvco_pts = sorted([r for r in rows if ok(r) and r["temp_C"] == 27.0 and r["corner"] == "tt"],
                       key=lambda r: r["vctrl_V"])
    print("\n-- K_VCO tuning curve (T=27C, tt corner) --")
    for r in kvco_pts:
        flag = " [LOW CONFIDENCE]" if r.get("low_confidence") else ""
        idd = f", Idd={r['i_avg_A']*1e3:.4f} mA" if r.get("i_avg_A") is not None else ""
        print(f"  Vctrl={r['vctrl_V']:.2f} V -> f_osc={r['freq_mhz']:.3f} MHz "
              f"(n_periods={r['n_periods']}{idd}){flag}")

    fit_pts = [r for r in kvco_pts if not r.get("low_confidence")]
    if len(fit_pts) >= 3:
        xs = [r["vctrl_V"] for r in fit_pts]
        ys = [r["freq_mhz"] for r in fit_pts]
        deg = min(2, len(fit_pts) - 1)
        coeffs = poly_fit(xs, ys, deg)
        print(f"\n  Degree-{deg} fit f_osc(Vctrl) [high-confidence points only, "
              f"n={len(fit_pts)}]: " + " + ".join(f"{c:.3g}*Vc^{p}" for p, c in enumerate(coeffs)))
        for vc in (0.9,):
            if min(xs) <= vc <= max(xs):
                print(f"  K_VCO at Vctrl={vc}V (fit derivative): "
                      f"{poly_deriv_eval(coeffs, vc):.1f} MHz/V "
                      f"(NOTE: two-point secants elsewhere on this curve differ "
                      f"visibly -- curve is measurably nonlinear, do not quote a single "
                      f"scalar K_VCO without stating the bias point it's evaluated at)")
    else:
        print("  Not enough high-confidence points for a fit.")

    # Uncompensated temperature baseline: fixed vctrl=0.9, varying temp (tt only)
    temp_pts = sorted([r for r in rows if ok(r) and abs(r["vctrl_V"] - 0.9) < 1e-6
                        and r["corner"] == "tt"],
                       key=lambda r: r["temp_C"])
    print("\n-- Uncompensated temperature baseline (Vctrl=0.9V, tt corner) --")
    for r in temp_pts:
        idd = f", Idd={r['i_avg_A']*1e3:.4f} mA" if r.get("i_avg_A") is not None else ""
        print(f"  T={r['temp_C']:+.0f}C -> f_osc={r['freq_mhz']:.3f} MHz{idd}")

    if len(temp_pts) >= 2:
        f_nom = next((r["freq_mhz"] for r in temp_pts if r["temp_C"] == 27.0), temp_pts[0]["freq_mhz"])
        print("\n  Per-interval local tempco (NOT a single scalar -- see charter critique item 5):")
        for a, b in zip(temp_pts, temp_pts[1:]):
            dT = b["temp_C"] - a["temp_C"]
            ppm = (b["freq_mhz"] - a["freq_mhz"]) / f_nom / dT * 1e6
            print(f"    {a['temp_C']:+.0f}C -> {b['temp_C']:+.0f}C : {ppm:+.0f} ppm/C")

        xs = [r["temp_C"] for r in temp_pts]
        ys = [r["freq_mhz"] for r in temp_pts]
        deg = min(2, len(temp_pts) - 1)
        coeffs = poly_fit(xs, ys, deg)
        f_lo, f_hi = temp_pts[0]["freq_mhz"], temp_pts[-1]["freq_mhz"]
        t_lo, t_hi = temp_pts[0]["temp_C"], temp_pts[-1]["temp_C"]
        span_pct = (f_hi - f_lo) / f_nom * 100
        print(f"\n  Endpoint secant (-40C to 85C): {span_pct:.2f}% of nominal, "
              f"{(f_hi - f_lo) / f_nom / (t_hi - t_lo) * 1e6:.0f} ppm/C average "
              f"-- reported ONLY as a headline summary; the per-interval table above is "
              f"the number that should drive compensation-network design and the C "
              f"(compensation ratio) definition.")
        print(f"  Degree-{deg} fit f_osc(T): " +
              " + ".join(f"{c:.4g}*T^{p}" for p, c in enumerate(coeffs)))
        print(f"  Fit-derivative tempco at T=27C: "
              f"{poly_deriv_eval(coeffs, 27.0) / f_nom * 1e6:.0f} ppm/C")

    # Corner-shape check (charter critique item 3): is the tempco CURVE SHAPE
    # stable across ss/ff, or only its magnitude? Only 3 temp points per
    # corner here (cheap spot-check) -- not a substitute for the full PVT
    # sweep planned for Review 2, just a check that nothing qualitatively
    # different is happening before compensation-network design starts.
    print("\n-- Corner-shape spot check (Vctrl=0.9V, -40/27/85C only) --")
    for corner in ("ss", "sf", "tt", "fs", "ff"):
        pts = sorted([r for r in rows if ok(r) and abs(r["vctrl_V"] - 0.9) < 1e-6
                      and r["corner"] == corner], key=lambda r: r["temp_C"])
        if len(pts) < 2:
            continue
        f_nom_c = next((r["freq_mhz"] for r in pts if r["temp_C"] == 27.0), pts[0]["freq_mhz"])
        span = (pts[-1]["freq_mhz"] - pts[0]["freq_mhz"]) / f_nom_c * 100
        ppm = (pts[-1]["freq_mhz"] - pts[0]["freq_mhz"]) / f_nom_c / (pts[-1]["temp_C"] - pts[0]["temp_C"]) * 1e6
        print(f"  {corner}: f(27C)={f_nom_c:.1f} MHz, span(-40->85C)={span:+.2f}% of nominal, "
              f"avg tempco={ppm:+.0f} ppm/C")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
