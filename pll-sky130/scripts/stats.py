#!/usr/bin/env python3
"""Minimal stats toolkit -- no scipy/numpy (not installed, and this is small
enough that pulling in a heavy dependency isn't worth it). Covers exactly
what the project's hypothesis tests need: paired comparison (t-test +
Wilcoxon signed-rank as a corroborating check), and OLS regression with a
CI on the slope for the H1 (eps_res ~ C * eps_raw) test.

Methodology per the research pass in docs/stats_methodology.md: report
CIs and let "does the CI exclude 0 (or 1)" stand in for a p-value -- that's
a valid, equivalent way to do the test without needing an incomplete-beta
p-value calculator.
"""
import math

# Two-tailed 95% critical t-values, df -> t. >30 converges to the normal
# z=1.96 (agent research: n>=30 makes the t/z distinction immaterial here).
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}


def t_crit_95(df):
    if df in _T95:
        return _T95[df]
    if df < 1:
        return float("nan")
    return 1.960  # normal approximation for df > 30


def mean(xs):
    return sum(xs) / len(xs)


def sample_std(xs):
    m = mean(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def ci95(xs):
    """Mean +/- 95% CI half-width, via t-distribution (df=n-1)."""
    n = len(xs)
    m = mean(xs)
    if n < 2:
        return m, 0.0
    s = sample_std(xs)
    hw = t_crit_95(n - 1) * s / math.sqrt(n)
    return m, hw


def paired_ttest(a, b):
    """Paired t-test on (a - b). Returns dict with mean diff, 95% CI,
    t-statistic, df, and whether the CI excludes 0 (= significant at 95%)."""
    assert len(a) == len(b) and len(a) >= 2, "need >=2 paired samples"
    diffs = [x - y for x, y in zip(a, b)]
    m, hw = ci95(diffs)
    n = len(diffs)
    s = sample_std(diffs)
    t_stat = m / (s / math.sqrt(n)) if s > 0 else float("inf")
    return {
        "n": n, "mean_diff": m, "ci95_halfwidth": hw,
        "ci95_lo": m - hw, "ci95_hi": m + hw,
        "t_stat": t_stat, "df": n - 1,
        "significant_95": (m - hw > 0) or (m + hw < 0),
    }


def wilcoxon_signed_rank(a, b):
    """Normal-approximation Wilcoxon signed-rank test on (a - b). Valid for
    n large enough that the rank-sum statistic is approximately normal
    (rule of thumb n>=10ish, per research pass) -- use as a corroborating
    check alongside the paired t-test, not a replacement for small n."""
    diffs = [x - y for x, y in zip(a, b) if x != y]
    n = len(diffs)
    if n < 4:
        return {"n": n, "note": "too few nonzero pairs for a meaningful W"}
    ranked = sorted(range(n), key=lambda i: abs(diffs[i]))
    ranks = [0.0] * n
    for pos, i in enumerate(ranked):
        ranks[i] = pos + 1
    # average tied ranks (ties in |diff|)
    abs_sorted = sorted(abs(diffs[i]) for i in range(n))
    i = 0
    while i < n:
        j = i
        while j < n and abs_sorted[j] == abs_sorted[i]:
            j += 1
        if j - i > 1:
            avg_rank = sum(range(i + 1, j + 1)) / (j - i)
            for k in ranked:
                if abs(diffs[k]) == abs_sorted[i]:
                    ranks[k] = avg_rank
        i = j
    w_plus = sum(ranks[i] for i in range(n) if diffs[i] > 0)
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w_plus - mu) / sigma if sigma > 0 else float("inf")
    return {"n": n, "w_plus": w_plus, "z": z, "significant_95": abs(z) > 1.96}


def ols_regression(xs, ys):
    """Simple linear regression y = a + b*x, with 95% CI on b and R^2."""
    n = len(xs)
    assert n == len(ys) and n >= 3, "need >=3 points for a regression"
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    b = sxy / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    sse = sum(r ** 2 for r in resid)
    df = n - 2
    if df < 1 or sxx == 0:
        return {"n": n, "slope": b, "intercept": a, "r2": None, "note": "df<1, no CI"}
    s2 = sse / df
    se_b = math.sqrt(s2 / sxx)
    hw = t_crit_95(df) * se_b
    r2 = 1 - sse / syy if syy > 0 else float("nan")
    return {
        "n": n, "slope": b, "intercept": a, "r2": r2,
        "slope_se": se_b, "slope_ci95_lo": b - hw, "slope_ci95_hi": b + hw,
        "df": df,
        "excludes_zero": (b - hw > 0) or (b + hw < 0),
        "excludes_one": (b - hw > 1) or (b + hw < 1),
    }


def mc_sample_size(pilot_std, target_margin, z=1.96):
    """n = (z*sigma/E)^2, per the standard mean-CI sample-size formula.
    Run a pilot batch (recommended n=30) first to get pilot_std."""
    return math.ceil((z * pilot_std / target_margin) ** 2)


if __name__ == "__main__":
    # self-check: a case with a known answer
    a = [10, 12, 9, 11, 13, 8, 10, 12]
    b = [8, 9, 7, 8, 10, 6, 9, 9]
    r = paired_ttest(a, b)
    assert r["significant_95"], "expected a to be significantly > b"
    assert abs(r["mean_diff"] - sum(x - y for x, y in zip(a, b)) / len(a)) < 1e-9

    w = wilcoxon_signed_rank(a, b)
    assert w["significant_95"]

    xs = [0, 1, 2, 3, 4, 5]
    ys = [1, 3, 5, 7, 9, 11]  # y = 1 + 2x exactly
    reg = ols_regression(xs, ys)
    assert abs(reg["slope"] - 2.0) < 1e-9
    assert reg["r2"] > 0.999

    n = mc_sample_size(pilot_std=50, target_margin=20)
    assert n == math.ceil((1.96 * 50 / 20) ** 2)

    print("stats.py self-check OK")
