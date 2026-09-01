#!/usr/bin/env python3
"""
Extract oscillation frequency from an ngspice `wrdata` transient dump
(two columns: time, v(vout)) via rising mid-rail threshold crossings.

Usage: extract_freq.py <file.txt> [--vdd 1.8] [--skip-frac 0.3] [--json]
"""
import sys
import argparse
import json


def load_columns(path):
    t, v = [], []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                tv, vv = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            t.append(tv)
            v.append(vv)
    return t, v


def rising_crossings(t, v, thresh):
    crossings = []
    for i in range(1, len(v)):
        if v[i - 1] < thresh <= v[i]:
            # linear interpolation for sub-step crossing time
            t0, t1 = t[i - 1], t[i]
            v0, v1 = v[i - 1], v[i]
            frac = (thresh - v0) / (v1 - v0) if v1 != v0 else 0.0
            crossings.append(t0 + frac * (t1 - t0))
    return crossings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--vdd", type=float, default=1.8)
    ap.add_argument("--skip-frac", type=float, default=0.3,
                     help="fraction of total sim time to discard as startup transient")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    t, v = load_columns(args.file)
    if len(t) < 10:
        print(json.dumps({"error": "insufficient data points", "n": len(t)}))
        sys.exit(1)

    tmax = t[-1]
    skip_t = args.skip_frac * tmax
    keep_idx = [i for i, tv in enumerate(t) if tv >= skip_t]
    t2 = [t[i] for i in keep_idx]
    v2 = [v[i] for i in keep_idx]

    thresh = args.vdd / 2.0
    crossings = rising_crossings(t2, v2, thresh)

    result = {
        "file": args.file,
        "n_samples": len(t),
        "t_start": t[0],
        "t_stop": t[-1],
        # v_min/v_max deliberately computed on the POST-SKIP window (v2), not
        # the raw record -- the raw record includes the cold-start transient,
        # and reporting rail-violation claims from that window conflates a
        # startup artifact with real steady-state ringing (see charter/review
        # critique F1). If you want the raw-record extrema, compute them from
        # `v` before this point, but label them explicitly as pre-skip.
        "v_min_steady": min(v2) if v2 else None,
        "v_max_steady": max(v2) if v2 else None,
        "skip_time_s": skip_t,
        "n_rising_crossings_analyzed": len(crossings),
    }

    if len(crossings) < 3:
        result["error"] = "fewer than 3 rising crossings after startup skip -- not oscillating, not settled, or swing doesn't cross Vdd/2"
        print(json.dumps(result, indent=2) if args.json else result)
        sys.exit(2)

    periods = [crossings[i + 1] - crossings[i] for i in range(len(crossings) - 1)]
    mean_period = sum(periods) / len(periods)
    freq = 1.0 / mean_period
    # NOT a jitter/phase-noise measurement: this is a fully deterministic
    # transient (no .noise, no mismatch, fixed seed-free sim), so cycle-to-
    # cycle period spread here can only come from residual settling or
    # timestep/interpolation error -- it is a settling sanity check, nothing
    # more. Do not report this as jitter or promote it into a phase-noise
    # number; that estimate requires a noise source (Review 2/3 scope).
    var = sum((p - mean_period) ** 2 for p in periods) / len(periods)
    std = var ** 0.5
    MIN_PERIODS_FOR_CONFIDENCE = 10
    result.update({
        "n_periods": len(periods),
        "mean_period_s": mean_period,
        "period_regularity_frac": std / mean_period if mean_period else None,
        "freq_hz": freq,
        "freq_mhz": freq / 1e6,
        "low_confidence": len(periods) < MIN_PERIODS_FOR_CONFIDENCE,
    })
    if result["low_confidence"]:
        result["warning"] = (f"only {len(periods)} periods captured after skip -- "
                              f"below the {MIN_PERIODS_FOR_CONFIDENCE}-period confidence "
                              f"threshold; treat this frequency as provisional, extend TSTOP")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        flag = " [LOW CONFIDENCE]" if result["low_confidence"] else ""
        print(f"{args.file}: f_osc = {freq/1e6:.3f} MHz  "
              f"(n_periods={len(periods)}, regularity={result['period_regularity_frac']:.4f}, "
              f"vmin={result['v_min_steady']:.3f}, vmax={result['v_max_steady']:.3f}){flag}")

    return result


if __name__ == "__main__":
    main()
