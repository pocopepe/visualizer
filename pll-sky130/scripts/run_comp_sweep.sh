#!/usr/bin/env bash
# Same as run_sweep.sh but for the compensated VCO testbench (adds k1,k2
# coefficients to each point). See run_sweep.sh for the parse-cost/
# parallelism rationale -- unchanged here.
#
# Usage: run_comp_sweep.sh <outdir> <jobs> <point1> <point2> ...
#   each point is "corner:temp:vctrl:tstep:tstop:k1:k2"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/env/pdk.env" >/dev/null

OUTDIR=$1; JOBS=$2; shift 2
mkdir -p "$OUTDIR"
VCO_INC="$ROOT/blocks/vco/vco_ring.spice"
TEMPLATE="$ROOT/blocks/vco/tb_comp_template.spice"

gen_and_run() {
  point="$1"
  IFS=':' read -r corner temp vctrl tstep tstop k1 k2 <<< "$point"
  tag="${corner}_T${temp}_Vc${vctrl}_k1${k1}_k2${k2}"
  cir="$OUTDIR/${tag}.cir"
  out="$OUTDIR/${tag}.txt"
  log="$OUTDIR/${tag}.log"
  sed -e "s#__SPICE_MODELS__#${SPICE_MODELS}#g" \
      -e "s#__CORNER__#${corner}#g" \
      -e "s#__TEMP__#${temp}#g" \
      -e "s#__VCTRL__#${vctrl}#g" \
      -e "s#__TSTEP__#${tstep}#g" \
      -e "s#__TSTOP__#${tstop}#g" \
      -e "s#__K1__#${k1}#g" \
      -e "s#__K2__#${k2}#g" \
      -e "s#__OUTFILE__#${out}#g" \
      -e "s#\"vco_ring.spice\"#\"${VCO_INC}\"#g" \
      "$TEMPLATE" > "$cir"
  timeout 240 ngspice -b "$cir" < /dev/null > "$log" 2>&1
  status=$?
  freqline=$(python3 "$ROOT/scripts/extract_freq.py" "$out" 2>&1 | tail -1)
  echo "[$tag] exit=$status  $freqline"
}
export -f gen_and_run
export ROOT OUTDIR SPICE_MODELS VCO_INC TEMPLATE

printf '%s\n' "$@" | xargs -P "$JOBS" -I{} bash -c 'gen_and_run "$@"' _ {}
