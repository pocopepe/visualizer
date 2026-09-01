#!/usr/bin/env python3
"""Quick functional checks for the DIV8 and PFD standalone testbenches."""
import sys


def load_pairs(path, col_pair):
    """wrdata repeats (time, value) per signal -- col_pair=(0,1) for the
    first signal, (2,3) for the second, etc."""
    t, v = [], []
    ti, vi = col_pair
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) <= vi:
                continue
            t.append(float(p[ti]))
            v.append(float(p[vi]))
    return t, v


def rising_edges(t, v, thresh=0.9):
    edges = []
    for i in range(1, len(v)):
        if v[i - 1] < thresh <= v[i]:
            edges.append(t[i])
    return edges


def pulse_widths(t, v, thresh=0.9):
    """Return list of (start_time, width) for each high pulse."""
    widths = []
    start = None
    for i in range(1, len(v)):
        if v[i - 1] < thresh <= v[i]:
            start = t[i]
        elif v[i - 1] >= thresh > v[i] and start is not None:
            widths.append((start, t[i] - start))
            start = None
    return widths


def check_divider(path):
    print("=== DIV8 check ===")
    t_clk, v_clk = load_pairs(path, (0, 1))
    t_q, v_q = load_pairs(path, (2, 3))
    clk_edges = rising_edges(t_clk, v_clk)
    q_edges = rising_edges(t_q, v_q)
    if len(clk_edges) < 2 or len(q_edges) < 2:
        print(f"  FAIL: too few edges (clk={len(clk_edges)}, q={len(q_edges)})")
        return
    clk_period = (clk_edges[-1] - clk_edges[0]) / (len(clk_edges) - 1)
    q_period = (q_edges[-1] - q_edges[0]) / (len(q_edges) - 1)
    ratio = q_period / clk_period
    print(f"  clk period={clk_period*1e9:.3f} ns ({1/clk_period/1e6:.2f} MHz), "
          f"n_edges={len(clk_edges)}")
    print(f"  qout period={q_period*1e9:.3f} ns ({1/q_period/1e6:.2f} MHz), "
          f"n_edges={len(q_edges)}")
    print(f"  ratio qout/clk period = {ratio:.3f} (expect 8.000 for /8)")
    print(f"  {'PASS' if abs(ratio - 8.0) < 0.05 else 'FAIL'}")


def check_pfd(path):
    print("=== PFD check ===")
    t_ref, v_ref = load_pairs(path, (0, 1))
    t_div, v_div = load_pairs(path, (2, 3))
    t_up, v_up = load_pairs(path, (4, 5))
    t_dn, v_dn = load_pairs(path, (6, 7))
    up_pulses = pulse_widths(t_up, v_up)
    dn_pulses = pulse_widths(t_dn, v_dn)
    print(f"  UP pulses: {len(up_pulses)}, DN pulses: {len(dn_pulses)}")
    if up_pulses:
        widths = [w for _, w in up_pulses]
        print(f"  UP width range: {min(widths)*1e9:.3f} - {max(widths)*1e9:.3f} ns")
    if dn_pulses:
        widths = [w for _, w in dn_pulses]
        print(f"  DN width range: {min(widths)*1e9:.3f} - {max(widths)*1e9:.3f} ns")
    # Sanity: since ref (20MHz) is faster than div (18MHz), ref should lead
    # more and more over time -> UP pulses should generally be wider than DN,
    # and both should grow as the beat progresses, resetting each beat cycle.
    both_present = len(up_pulses) > 3 and len(dn_pulses) > 3
    print(f"  Both UP and DN pulses observed across the beat sweep: "
          f"{'PASS' if both_present else 'FAIL'}")
    avg_up = sum(w for _, w in up_pulses) / len(up_pulses) if up_pulses else 0
    avg_dn = sum(w for _, w in dn_pulses) / len(dn_pulses) if dn_pulses else 0
    print(f"  avg UP width={avg_up*1e9:.2f}ns, avg DN width={avg_dn*1e9:.2f}ns "
          f"(ref runs faster than div overall, so UP-heavy is expected)")


if __name__ == "__main__":
    check_divider(sys.argv[1])
    print()
    check_pfd(sys.argv[2])
