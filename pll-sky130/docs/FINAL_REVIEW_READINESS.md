# Final-review readiness (as of 2026-10-20)

Honest snapshot of what is finished, what is verified, and what is still open. Companion files: `STATUS.md` (checklists), `RESULTS.md` (all numbers), `docs/review2_guide/review2_guide.tex` (talking points and Q&A), `PROJECT_CHARTER.md` (decision log).

## Finished and verified
| Area | Result | Evidence |
|---|---|---|
| Corner audit (new) | PDK skew corners are wider than ss/ff (outside the envelope at 0.9 V); textbook 3x3 NMOS x PMOS set, all ordering checks pass; sims reproduce on ngspice 47 | `results/corner_audit/FINDINGS.md` |
| VCO, 5 PDK corners x 6 temperatures | tempco 112 / 332 / 681 / 1070 / 1399 ppm/C (sf/ff/tt/ss/fs), 12.5x spread; tempco ranks with NMOS drive; sign flip at Vctrl = 1.4 V | `results/vco/`, `docs/sensitivity_analysis.md` |
| Local K_VCO at 0.9 V | 580 / 940 / 890 / 820 / 1020 MHz/V (sf/ff/tt/ss/fs) | `results/vco/kvco_fine/` |
| Compensation (ideal behavioural, nominal) | tt span 8.51 % -> 0.20 % (max dev 0.16 %, spec met); 8 of 11 corners meet +/-0.3 % (misses: N slow/P typ 0.301 borderline, N slow/P fast 0.325, PDK fs 0.360) | `results/comp/FINDINGS_FINAL.md`, `results/final_numbers.md` |
| Monte Carlo (tt, n = 72, paired) | both networks cut drift 20.1 -> 3.2 / 2.8 MHz; 2nd order NOT significantly better than 1st (0.49 MHz, CI [-0.26, 1.24]); mismatch floor ~1.2-1.4 % | `results/comp/mc_v2_analysis.txt`, `docs/stats_methodology.md` |
| Loop filter / closed loop | retuned R2 = 3.6 kOhm (zeta 0.33 -> ~0.70); 28-run campaign: locks at all 11 corners at 27 C (177-1675 ns), f_VCO = 8 x f_ref in every run; ss at 85 C cold start 2083 ns MISSES the 2 us spec by 4 % | `results/loop/campaign/summary.csv` |
| Tooling | ngspice, Magic, KLayout, real netgen (`~/tools/netgen/bin/netgen`) | `env/NETGEN.md` |

## Corrections made after Review 2 (be ready to explain)
sf/fs labels were reversed; tempco mechanism rewritten; K_VCO was 669, really ~890 MHz/V; "0.63 V oscillation floor" was a short-window artefact; Review-1 loop design dropped a 1/(2 pi) (zeta 0.33, retuned); compensation coefficients re-fitted after the K_VCO error (tt 0.87 % -> 0.16 % max dev); Monte Carlo redone with the correct coefficients (2nd order not significantly better, n = 72). Open-loop VCO characterisation (tempcos, K_VCO) was only relabelled/re-measured, not changed. Details in `STATUS.md` errata and `PROJECT_CHARTER.md`.

## Known limitations (say them before the examiner does)
- Compensation is an ideal behavioural voltage, not transistors. Nominal spec met at 8 of 11 corners; with chip-to-chip mismatch the residual is ~1.2-1.4 % (a per-chip trim would be needed for +/-0.3 %).
- Charge pump is behavioural. The retune was verified with it; transistor-level CP may change dynamics.
- Cold start simulated at all 11 corners (27 C) and at -40/85 C for ss/tt/ff; ss at 85 C misses 2 us (2083 ns). Cold start got slower with the retune (839 -> 1351 ns at tt, still < 2 us).
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
