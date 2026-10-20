#!/usr/bin/env bash
# Generates and runs a batch of VCO_RING transient sims (one ngspice process
# per point -- each pays the ~45s sky130 model-parse cost, so points are run
# in parallel across cores rather than serially).
#
# Usage: run_sweep.sh <outdir> <jobs> <point1> <point2> ...
#   each point is "corner:temp:vctrl:tstep:tstop"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/env/pdk.env" >/dev/null
SPICE_MODELS="${MODELS_OVERRIDE:-$SPICE_MODELS}"   # e.g. env/sky130_factorial.lib.spice for the 3x3 textbook corners

OUTDIR=$1; JOBS=$2; shift 2
mkdir -p "$OUTDIR"
VCO_INC="$ROOT/blocks/vco/vco_ring.spice"
TEMPLATE="$ROOT/blocks/vco/tb_template.spice"

gen_and_run() {
  point="$1"
  IFS=':' read -r corner temp vctrl tstep tstop <<< "$point"
  tag="${corner}_T${temp}_Vc${vctrl}"
  cir="$OUTDIR/${tag}.cir"
  out="$OUTDIR/${tag}.txt"
  log="$OUTDIR/${tag}.log"
  sed -e "s#__SPICE_MODELS__#${SPICE_MODELS}#g" \
      -e "s#__CORNER__#${corner}#g" \
      -e "s#__TEMP__#${temp}#g" \
      -e "s#__VCTRL__#${vctrl}#g" \
      -e "s#__TSTEP__#${tstep}#g" \
      -e "s#__TSTOP__#${tstop}#g" \
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
