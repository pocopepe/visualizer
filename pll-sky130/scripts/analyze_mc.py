#!/usr/bin/env python3
"""Analyze the Monte Carlo compensation sweep (results/mc/*.txt).

Per trial (seed), per arm (baseline/1st-order/2nd-order), drift = f(85C) - f(-40C).
Arms are paired by seed (same mismatch instance), so paired tests are correct.

Compensation quality is the MAGNITUDE |drift|, not the signed drift: a network
that over-corrects (drift goes negative) and one that under-corrects (drift stays
positive) can differ significantly in signed drift while being equally good. The
first version of this script tested signed drift and reported 1st-vs-2nd as
significant purely because the sign flipped -- tests below are on |drift|.
"""
import glob
import json
import re
import subprocess
import sys

sys.path.insert(0, "scripts")
from stats import paired_ttest, wilcoxon_signed_rank, sample_std, ci95  # noqa: E402

ARMS = {
    "baseline": ("0", "0"),
    "1st_order": ("-2.163e-4", "0"),
    "2nd_order_refined": ("-1.321953e-4", "2.893555e-7"),
}
PAT = re.compile(r"tt_T(?P<temp>-?\d+)_k1(?P<k1>[^_]+)_k2(?P<k2>[^_]+)_seed(?P<seed>\d+)\.txt$")


def freq(path):
    out = subprocess.run([sys.executable, "scripts/extract_freq.py", path, "--json"],
                         capture_output=True, text=True)
    try:
        return json.loads(out.stdout).get("freq_mhz")
    except json.JSONDecodeError:
        return None


def load(mc_dir):
    drift = {}  # (arm, seed) -> f(85) - f(-40)
    temps = {}
    for f in glob.glob(f"{mc_dir}/*.txt"):
        m = PAT.search(f)
        if not m:
            continue
        arm = next((a for a, (k1, k2) in ARMS.items() if (k1, k2) == (m["k1"], m["k2"])), None)
        if arm:
            temps.setdefault((arm, int(m["seed"])), {})[int(m["temp"])] = freq(f)
    for key, t in temps.items():
        if t.get(-40) and t.get(85):
            drift[key] = t[85] - t[-40]
    return drift


def paired(drift, a, b):
    """Pairs built per seed, so a missing point in one arm can't misalign the rest."""
    seeds = sorted(s for (arm, s) in drift if arm == a and (b, s) in drift)
    return [drift[(a, s)] for s in seeds], [drift[(b, s)] for s in seeds]


def main(mc_dir="results/mc"):
    drift = load(mc_dir)
    for arm in ARMS:
        vals = [v for (a, _), v in drift.items() if a == arm]
        if not vals:
            continue
        m, hw = ci95(vals)
        am, ahw = ci95([abs(v) for v in vals])
        print(f"{arm} (n={len(vals)}): signed drift mean={m:.3f} MHz [{m-hw:.3f}, {m+hw:.3f}], "
              f"std={sample_std(vals):.3f} | |drift| mean={am:.3f} MHz [{am-ahw:.3f}, {am+ahw:.3f}]")
    print()
    for a, b in [("baseline", "1st_order"), ("baseline", "2nd_order_refined"),
                 ("1st_order", "2nd_order_refined")]:
        va, vb = paired(drift, a, b)
        if len(va) < 2:
            print(f"{a} vs {b}: not enough paired trials (n={len(va)})")
            continue
        ma, mb = [abs(x) for x in va], [abs(x) for x in vb]
        t = paired_ttest(ma, mb)
        w = wilcoxon_signed_rank(ma, mb)
        wins = sum(y < x for x, y in zip(ma, mb))
        print(f"{a} vs {b} (n={len(va)}): |drift| reduction={t['mean_diff']:.3f} MHz, "
              f"95% CI=[{t['ci95_lo']:.3f}, {t['ci95_hi']:.3f}], paired-t significant={t['significant_95']}, "
              f"wilcoxon significant={w.get('significant_95')}, {b} smaller in {wins}/{len(va)} seeds")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/mc")
