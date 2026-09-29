#!/usr/bin/env python3
"""Analyze the Monte Carlo compensation sweep (results/mc/*.txt).

Per trial (seed), per arm (baseline/1st-order/2nd-order), computes the
drift metric f(85C) - f(-40C) -- paired across arms via the SAME seed, so
paired_ttest/wilcoxon in stats.py are the statistically correct tools here
(same mismatch instance run through each arm, not independent samples).
"""
import glob
import json
import re
import subprocess
import sys

sys.path.insert(0, "scripts")
from stats import paired_ttest, wilcoxon_signed_rank, mean, sample_std, ci95  # noqa: E402

ARMS = {
    "baseline": ("0", "0"),
    "1st_order": ("-2.163e-4", "0"),
    "2nd_order_refined": ("-1.321953e-4", "2.893555e-7"),
}


def freq(path):
    out = subprocess.run([sys.executable, "scripts/extract_freq.py", path, "--json"],
                          capture_output=True, text=True)
    try:
        return json.loads(out.stdout).get("freq_mhz")
    except json.JSONDecodeError:
        return None


def main(mc_dir="results/mc"):
    files = glob.glob(f"{mc_dir}/*.txt")
    # tag: tt_T{temp}_k1{k1}_k2{k2}_seed{seed}
    pat = re.compile(r"tt_T(?P<temp>-?\d+)_k1(?P<k1>[^_]+)_k2(?P<k2>[^_]+)_seed(?P<seed>\d+)\.txt$")

    data = {}  # (arm, seed) -> {temp: freq}
    for f in files:
        m = pat.search(f)
        if not m:
            continue
        temp = int(m["temp"])
        seed = int(m["seed"])
        arm = next((a for a, (k1, k2) in ARMS.items() if k1 == m["k1"] and k2 == m["k2"]), None)
        if arm is None:
            continue
        fr = freq(f)
        data.setdefault((arm, seed), {})[temp] = fr

    metrics = {arm: [] for arm in ARMS}
    for (arm, seed), temps in data.items():
        if -40 in temps and 85 in temps and temps[-40] and temps[85]:
            metrics[arm].append(temps[85] - temps[-40])

    print(f"Trials per arm: " + ", ".join(f"{a}={len(v)}" for a, v in metrics.items()))
    print()
    for arm, vals in metrics.items():
        if not vals:
            continue
        m, hw = ci95(vals)
        print(f"{arm}: drift(85C)-drift(-40C) mean={m:.3f} MHz, "
              f"std={sample_std(vals):.3f}, 95% CI=[{m-hw:.3f}, {m+hw:.3f}] (n={len(vals)})")

    print()
    pairs = [("baseline", "1st_order"), ("1st_order", "2nd_order_refined"), ("baseline", "2nd_order_refined")]
    for a, b in pairs:
        common_seeds = sorted(set(s for (arm, s) in data if arm == a) & set(s for (arm, s) in data if arm == b))
        va = [data[(a, s)][85] - data[(a, s)][-40] for s in common_seeds
              if 85 in data[(a, s)] and -40 in data[(a, s)] and data[(a, s)][85] and data[(a, s)][-40]]
        vb = [data[(b, s)][85] - data[(b, s)][-40] for s in common_seeds
              if 85 in data[(b, s)] and -40 in data[(b, s)] and data[(b, s)][85] and data[(b, s)][-40]]
        n = min(len(va), len(vb))
        if n < 2:
            print(f"{a} vs {b}: not enough paired trials (n={n})")
            continue
        va, vb = va[:n], vb[:n]
        tt = paired_ttest(va, vb)
        w = wilcoxon_signed_rank(va, vb)
        print(f"{a} vs {b} (n={n}): mean_diff={tt['mean_diff']:.3f} MHz, "
              f"95% CI=[{tt['ci95_lo']:.3f}, {tt['ci95_hi']:.3f}], "
              f"significant_95={tt['significant_95']} "
              f"(paired t) | wilcoxon significant_95={w.get('significant_95')}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/mc")
