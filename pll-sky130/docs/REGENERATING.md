# Regenerating the raw simulation data

The repository tracks **summaries** (`.csv`, `.json`, `.md`, figures) but not the multi-MB raw ngspice waveforms (`results/**/*.txt`), logs and generated netlists. Everything can be regenerated; all commands run from `pll-sky130/` after `source env/pdk.env` (see the README for tool versions and the pinned PDK). Each ngspice process takes ~20 s; the scripts run many in parallel (`.spiceinit` sets one thread per process).

| Result set | Command(s) | Produces |
|---|---|---|
| VCO PVT grid (5 PDK corners x 6 T, Vctrl sweep) | `./scripts/run_sweep.sh results/vco/grid5corner 15 <corner:T:Vctrl:10p:400n ...>` then `python3 scripts/compile_vco_results.py <dir> results/vco/grid5corner.csv` | `results/vco/grid5corner.csv` |
| Quick demo of Review-1 numbers | `./scripts/demo_review1.sh --fast` (~4 min) | prints tempcos, closed-loop lock |
| Fine K_VCO sweep (0.85-0.95 V) | `run_sweep.sh results/vco/kvco_fine 15 <corner:27:{0.85,0.875,0.925}:10p:400n ...>` | `results/vco/kvco_fine/kvco_local.json` is tracked |
| Oscillation-floor / ZTC check | `run_sweep.sh results/vco/floor_check 6 tt:27:0.5:50p:20u tt:27:0.55:50p:10u tt:27:0.6:20p:4u tt:27:1.4:10p:400n tt:-40:1.4:10p:400n tt:85:1.4:10p:400n` | f at low V and 1.4 V |
| Single-device corner audit | `python3 scripts/corner_audit.py` | `results/corner_audit/device_corners.csv` |
| Textbook 3x3 corner library | `python3 scripts/make_factorial_lib.py` (writes `env/sky130_factorial.lib.spice`, not tracked) | library with sections `n{s,t,f}p{s,t,f}` |
| 9-corner VCO grid + ordering checks | `MODELS_OVERRIDE=$PWD/env/sky130_factorial.lib.spice ./scripts/run_sweep.sh results/vco/factorial 15 <n?p?:T:V:10p:400n ...> > results/vco/factorial/run.log`; `python3 scripts/factorial_analysis.py` | `results/vco/factorial.csv`, `results/corner_audit/factorial_summary.json` |
| Compensation fit + verification (11 corners) | `python3 scripts/comp_factorial.py [corner ...]` (use `pdk_sf pdk_fs` for the PDK skews) | `results/comp/factorial/factorial_comp*.json` |
| Monte Carlo (tt, n = 72) | `./scripts/run_comp_mc_sweep.sh results/mc_v2 15 tt:T:0.9:10p:400n:k1:k2:seed ...` (k1, k2 and seeds in `results/comp/FINDINGS_FINAL.md`; baseline arm k1 = k2 = 0 into `results/mc`), then `python3 scripts/analyze_mc.py --v2` | `results/comp/mc_v2_analysis.txt` |
| Closed-loop campaign (28 runs, R2 = 3.6 kOhm) | `python3 scripts/closed_loop_campaign.py` (~40 min on 16 cores) | `results/loop/campaign/summary.csv` and per-case `.json` |
| R2 retune study | commands in `results/loop/FINDINGS_RETUNE.md` | `results/loop/retune*/` |
| Figure data and figures | `python3 scripts/make_figdata.py` (needs the raw dumps above), `make_figures.py`, `make_audit_figures.py`, `make_final_figures.py`, `make_final_numbers.py` | `results/figdata.json` (tracked), `docs/figures/*.png`, `results/final_numbers.md` |
| Decks and guides | `scripts/make_deck_charts.py`, `scripts/make_final_deck.py`; LaTeX in `docs/*/` | files under `docs/reviews/` |

`results/figdata.json` and `results/final_numbers.md` already contain every number the figures and tables use, so the documents can be rebuilt without re-running simulations (except `make_figdata.py` itself).
