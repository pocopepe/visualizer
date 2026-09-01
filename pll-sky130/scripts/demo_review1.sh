#!/usr/bin/env bash
# Review 1 demo: regenerates every simulated result this project claims,
# from scratch, and prints the final numbers at the end. Headless, no GUI.
#
# Usage:
#   ./scripts/demo_review1.sh            # run everything (~8-12 min)
#   ./scripts/demo_review1.sh --fast     # skip the full VCO PVT sweep,
#                                        # reuse cached results (~3 min)
#
# Each ngspice invocation pays a ~45s one-time cost to parse the full sky130
# model library, then simulates in seconds -- most of the wall time below is
# that fixed cost paid once per test point, mitigated by running points in
# parallel across cores.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source env/pdk.env >/dev/null

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

hr() { printf '\n%s\n' "============================================================"; }
step() { hr; printf '  %s\n' "$1"; hr; }

# ------------------------------------------------------------------
step "1/4  VCO baseline: K_VCO tuning curve + uncompensated temp/corner sweep"
# ------------------------------------------------------------------
if [[ $FAST -eq 1 && -d results/vco/kvco_sweep ]]; then
  echo "(--fast: reusing cached results/vco/kvco_sweep -- delete that dir to force a rerun)"
else
  rm -rf results/vco/kvco_sweep
  mkdir -p results/vco/kvco_sweep
  KVCO_POINTS=(
    "tt:27:0.65:10p:3000n" "tt:27:0.7:10p:1000n" "tt:27:0.8:10p:400n"
    "tt:27:0.95:10p:400n" "tt:27:1.1:10p:400n" "tt:27:1.25:10p:400n" "tt:27:1.4:10p:400n"
  )
  TEMP_POINTS=(
    "tt:-40:0.9:10p:400n" "tt:-20:0.9:10p:400n" "tt:0:0.9:10p:400n"
    "tt:27:0.9:10p:400n" "tt:50:0.9:10p:400n" "tt:85:0.9:10p:400n"
  )
  CORNER_POINTS=(
    "ss:-40:0.9:10p:400n" "ss:27:0.9:10p:400n" "ss:85:0.9:10p:400n"
    "ff:-40:0.9:10p:400n" "ff:27:0.9:10p:400n" "ff:85:0.9:10p:400n"
  )
  ./scripts/run_sweep.sh results/vco/kvco_sweep 10 \
    "${KVCO_POINTS[@]}" "${TEMP_POINTS[@]}" "${CORNER_POINTS[@]}"
fi
python3 scripts/compile_vco_results.py results/vco/kvco_sweep results/vco/sweep_results_demo.csv

# ------------------------------------------------------------------
step "2/4  PFD + Divider: standalone functional verification"
# ------------------------------------------------------------------
sed "s#__SPICE_MODELS__#${SPICE_MODELS}#g" blocks/pfd/tb_pfd.spice > blocks/pfd/_run.cir
sed "s#__SPICE_MODELS__#${SPICE_MODELS}#g" blocks/divider/tb_divider.spice > blocks/divider/_run.cir
( cd blocks/pfd     && timeout 120 ngspice -b _run.cir < /dev/null > run.log 2>&1 ) &
( cd blocks/divider  && timeout 120 ngspice -b _run.cir < /dev/null > run.log 2>&1 ) &
wait
python3 scripts/verify_digital.py blocks/divider/results_div.txt blocks/pfd/results_pfd.txt

# ------------------------------------------------------------------
step "3/4  Closed loop: PFD -> Charge Pump -> Loop Filter -> VCO -> /8 -> PFD"
# ------------------------------------------------------------------
sed "s#__SPICE_MODELS__#${SPICE_MODELS}#g" blocks/top/tb_closed_loop.spice > blocks/top/_run.cir
( cd blocks/top && timeout 300 ngspice -b _run.cir < /dev/null > run.log 2>&1 )
mkdir -p results/loop
mv blocks/top/results_loop.txt results/loop/run_demo.txt
python3 scripts/analyze_closed_loop.py results/loop/run_demo.txt > results/loop/demo_summary.json
cat results/loop/demo_summary.json

# ------------------------------------------------------------------
step "4/4  CLAIMED NUMBERS -- summary"
# ------------------------------------------------------------------
python3 - << 'PYEOF'
import csv, json

print("\n--- VCO (results/vco/sweep_results_demo.csv) ---")
rows = list(csv.DictReader(open("results/vco/sweep_results_demo.csv")))
tt27 = [r for r in rows if r["corner"] == "tt" and r["temp_C"] == "27.0" and r["freq_mhz"]]
tt27.sort(key=lambda r: float(r["vctrl_V"]))
for r in tt27:
    print(f"  tt/27C  Vctrl={float(r['vctrl_V']):.2f}V  f_osc={float(r['freq_mhz']):.1f}MHz")

for corner in ("ff", "tt", "ss"):
    pts = sorted([r for r in rows if r["corner"] == corner and abs(float(r["vctrl_V"]) - 0.9) < 1e-6
                  and r["freq_mhz"]], key=lambda r: float(r["temp_C"]))
    if len(pts) >= 2:
        f_nom = next((float(r["freq_mhz"]) for r in pts if r["temp_C"] == "27.0"), float(pts[0]["freq_mhz"]))
        lo, hi = pts[0], pts[-1]
        ppm = (float(hi["freq_mhz"]) - float(lo["freq_mhz"])) / f_nom / (float(hi["temp_C"]) - float(lo["temp_C"])) * 1e6
        print(f"  {corner} corner uncompensated tempco: {ppm:+.0f} ppm/C")

print("\n--- Closed loop (results/loop/demo_summary.json) ---")
d = json.load(open("results/loop/demo_summary.json"))
for k, v in d.items():
    print(f"  {k}: {v}")

print("\n--- Claimed vs measured (this run) ---")
print(f"  Lock time:       claimed 577ns   | this run: {d.get('lock_time_ns')}ns   | spec: <2000ns")
print(f"  Settled Vctrl:   claimed 0.902V  | this run: {d.get('settled_vctrl_V')}V")
print(f"  VCO out freq:    claimed 227.96MHz | this run: {d.get('vco_out_freq_MHz')}MHz | target: {d.get('target_f_vco_MHz')}MHz")
PYEOF

hr
echo "Demo complete. Full writeups: RESULTS.md, results/vco/FINDINGS.md, results/loop/FINDINGS.md"
hr
