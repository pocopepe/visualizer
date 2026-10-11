# Final-review readiness (as of 2026-10-11)

Honest snapshot of what is finished, what is verified, and what is still open. Companion files: `STATUS.md` (checklists), `RESULTS.md` (all numbers), `docs/review2_guide/review2_guide.tex` (talking points and Q&A), `PROJECT_CHARTER.md` (decision log).

## Finished and verified
| Area | Result | Evidence |
|---|---|---|
| VCO, 5 corners x 6 temperatures | tempco 112 / 332 / 681 / 1070 / 1399 ppm/C (sf/ff/tt/ss/fs), 12.5x spread; tempco ranks with NMOS drive; sign flip at Vctrl = 1.4 V | `results/vco/`, `docs/sensitivity_analysis.md` |
| Local K_VCO at 0.9 V | 580 / 940 / 890 / 820 / 1020 MHz/V (sf/ff/tt/ss/fs) | `results/vco/kvco_fine/` |
| Compensation (ideal behavioural) | tt span 8.51 % -> 3.05 % -> 1.12 %; spec +/-0.3 % met at ff, sf only | `results/comp/` |
| Monte Carlo (tt, n = 30, paired) | 2nd-order beats 1st: -2.48 MHz, CI [0.81, 4.15], 23/30 seeds | `docs/stats_methodology.md` |
| Loop filter | retuned R2 = 3.6 kOhm: zeta 0.33 -> 0.70; locks at all 5 corners (241 / 419 / 503 / 576 / 967 ns, 0.85 V start); 0 V cold start 1352 ns at tt | `results/loop/retune*`, `docs/loop_model.md` |
| Tooling | ngspice, Magic, KLayout, real netgen (`~/tools/netgen/bin/netgen`) | `env/NETGEN.md` |

## Corrections made after Review 2 (be ready to explain)
sf/fs labels were reversed; tempco mechanism rewritten; K_VCO was 669, really ~890 MHz/V; "0.63 V oscillation floor" was a short-window artefact; Review-1 loop design dropped a 1/(2 pi) (zeta was 0.33, not 0.72), fixed by the R2 retune. Open-loop results (spans, tempcos, MC, held-out) were not affected. Details in `STATUS.md` errata and `PROJECT_CHARTER.md`.

## Known limitations (say them before the examiner does)
- Compensation is an ideal behavioural voltage, not transistors. Spec met at 2 of 5 corners.
- Charge pump is behavioural. The retune was verified with it; transistor-level CP may change dynamics.
- Cold start was simulated at tt only; corner lock tests use the 0.85 V coarse start. Cold start got slower with the retune (839 -> 1352 ns, still < 2 us).
- Phase margin (~65-70 deg) is the 100*zeta rule of thumb, not a Bode plot. Only R2 = 1.7 / 3.0 / 3.6 kOhm were simulated; 3.6 is not claimed optimal.
- The tempco mechanism (Vth drop beats mobility drop at low overdrive) is supported by ordering and the sign flip, not isolated per BSIM parameter.
- No jitter / phase-noise number (no PSS/Pnoise in open tools).
- Quadratic compensation is not novel (US 9,748,962 B2); the claim is the closed-loop, per-corner, statistically validated ring-VCO study on an open PDK.

## Still open for the final review (the Review 3 checklist)
| Item | Blocker / note |
|---|---|
| Transistor-level charge pump and compensation network | design work; re-run closed loop afterwards |
| Layout in Magic, DRC clean | not started |
| LVS via netgen | tool now installed; needs a layout + extracted netlist |
| Post-layout re-simulation | needs layout |
| Cadence/Virtuoso arm, Spectre PSS/Pnoise, GDS stream-in | **needs department Virtuoso access: confirm with Dr. Bindu now** (charter risk R1) |
| H1 regression (eps_res vs C) | needs the Spectre arm; the (alpha, C) points are ready (`results/comp/FINDINGS_H1_PIPELINE.md`) |
| Spec sign-offs (Vctrl floor revision, +/-0.15 ppm restatement) | needs Dr. Bindu |
| Paper draft + artifact release | after the above |

## Files to bring
`Design_of_a_Frequency_Synthesiser_Review-2.pptx/.pdf` (27 slides) and `Review-2_Reading_Guide.pdf` (cheatsheet) are in the repo root. Slide sources: `scripts/make_figdata.py` -> `scripts/make_figures.py` -> `scripts/make_deck_charts.py`.
