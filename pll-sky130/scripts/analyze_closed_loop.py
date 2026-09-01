#!/usr/bin/env python3
"""Extract lock time / settled frequencies from a closed-loop wrdata dump.
Columns (wrdata order): v(vctrl) v(vco_out) v(div_fb) v(up) v(dn)
-> pairs (0,1)=vctrl (2,3)=vco_out (4,5)=div_fb (6,7)=up (8,9)=dn
"""
import sys
import json


def load_pairs(path, ti, vi):
    t, v = [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) <= vi:
                continue
            t.append(float(p[ti]))
            v.append(float(p[vi]))
    return t, v


def main(path, settle_after=1.5e-6, band_frac=0.02, f_ref_target=28.275e6, n_div=8):
    t, vctrl = load_pairs(path, 0, 1)
    final_window = [v for tt, v in zip(t, vctrl) if tt > settle_after]
    if not final_window:
        print(json.dumps({"error": "no samples after settle_after -- run longer"}))
        sys.exit(1)
    vfinal = sum(final_window) / len(final_window)
    band = band_frac * vfinal

    lock_time = None
    for i in range(len(t)):
        if all(abs(v - vfinal) <= band for v in vctrl[i:]):
            lock_time = t[i]
            break

    def period_from_edges(ti, vi, thresh=0.9):
        tt, vv = load_pairs(path, ti, vi)
        last = [(a, b) for a, b in zip(tt, vv) if a > settle_after]
        edges = [last[i][0] for i in range(1, len(last)) if last[i - 1][1] < thresh <= last[i][1]]
        if len(edges) < 2:
            return None
        return (edges[-1] - edges[0]) / (len(edges) - 1)

    div_period = period_from_edges(4, 5)
    vco_period = period_from_edges(2, 3)

    result = {
        "settled_vctrl_V": round(vfinal, 4),
        "lock_time_ns": round(lock_time * 1e9, 1) if lock_time else None,
        "div_fb_freq_MHz": round(1 / div_period / 1e6, 3) if div_period else None,
        "vco_out_freq_MHz": round(1 / vco_period / 1e6, 3) if vco_period else None,
        "target_f_ref_MHz": round(f_ref_target / 1e6, 3),
        "target_f_vco_MHz": round(f_ref_target * n_div / 1e6, 1),
        "spec_lock_time_us": 2.0,
        "analytical_lock_time_ns": 450,
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/loop/run4_icfix.txt")
