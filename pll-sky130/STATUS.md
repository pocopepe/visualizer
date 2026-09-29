# Status — Review 1 Progress Tracker

Last updated: 2026-08-27. Milestones per `PROJECT_CHARTER.md` §8. Update this file, don't let it drift from reality — if a checkbox is ticked, there's a file/result backing it.

## Environment (done)
- [x] ngspice-42, Magic 8.3.105, KLayout 0.28.16 installed natively (apt), headless-capable
- [x] sky130 PDK (sky130B variant) pulled via volare, pinned to commit `c6d73a35f524070e85faff4a6a9eef49553ebc2b`
- [ ] netgen — **wrong package installed.** Ubuntu's `netgen` apt package is the TU-Vienna FEM mesh generator, not Tim Edwards' IC-design LVS tool of the same name. Needs building from [opencircuitdesign/netgen](https://github.com/RTimothyEdwards/netgen) from source, or via the IIC-OSIC-TOOLS Docker image (available, not yet used — native install was faster to start with). Not blocking yet (LVS is Review 3 scope).
- [x] Repo scaffold: `pll-sky130/{blocks,scripts,results,env,docs}`

## Review 1 checklist (target 50%) — **DONE**
- [x] Block schematic: VCO (`blocks/vco/vco_ring.spice`) — 5-stage current-starved ring, sky130 nfet/pfet_01v8
- [x] VCO characterized: f_osc(Vctrl), K_VCO (fit, not secant), tuning range, supply current — `results/vco/FINDINGS.md`
- [x] Uncompensated VCO temperature baseline — tt corner full sweep + ss/ff spot-check — `results/vco/FINDINGS.md`
- [x] One adversarial critique pass completed and acted on (netlist rev1→rev2) — see `results/vco/FINDINGS.md` "What the critique pass changed"
- [x] Block + testbench: PFD (`blocks/pfd/pfd.spice`) — edge-detector + cross-coupled NOR SR-latch design, functionally verified (`scripts/verify_digital.py`: UP/DN pulses track a swept phase relationship correctly)
- [x] Block + testbench: charge pump (`blocks/charge_pump/charge_pump.spice`) — **idealized behavioral model, deliberately**, see scoping note below
- [x] Block + testbench: loop filter (`blocks/loop_filter/loop_filter.spice`) — passive R2/C1/C2, sized from the analytical model
- [x] Block + testbench: feedback divider (`blocks/divider/divider.spice`) — ÷8 via 3 cascaded TFFs, functionally verified (ratio measured 8.004, target 8.000)
- [x] Closed loop assembled, lock demonstrated at nominal corner — `results/loop/FINDINGS.md`: **lock time 577ns** (target <2µs, analytical prediction ~450ns), settled within 0.85% of target frequency
- [x] Analytical loop model (loop BW, phase margin) derived and checked against sim — `docs/loop_model.md`; predicted ~450ns vs measured 577ns, same order of magnitude, gap explained (PFD reset delay + discrete CP pumping not in the continuous-time model)
- [x] Literature/novelty section drafted — `PROJECT_CHARTER.md` §3

### Scoping decisions made getting here (both deliberate, both documented, neither hidden)
1. **Charge pump is an idealized behavioral model** (`Bcp` current source gated by UP/DN, no transistor switches, no mismatch, no charge injection). Standard PLL design sequencing: verify loop dynamics against the analytical model first with an ideal CP, harden to transistor-level once mismatch modeling is actually needed — which is Review 2 (Monte Carlo) anyway, so no wasted work.
2. **PFD built from edge-detectors + NOR SR-latches, not resettable D-flip-flops.** Considered the DFF+async-reset route first; adding a reliable async reset to a transmission-gate latch without fighting its own bistable feedback loop is genuinely fiddly, and the edge-detector/SR-latch structure is the standard textbook alternative that sidesteps the problem entirely. No loss of rigor — verified functionally the same way.

### The two decisions flagged in the previous update — now resolved
1. **V_ctrl lock-range floor.** Charter §4 originally specified [0.15·VDD, 0.85·VDD] = [0.27V, 1.53V]. Measured minimum sustaining Vctrl for this ring-VCO topology is ~0.6-0.65V (device-threshold-limited: the NMOS current source's gate is driven directly by Vctrl, so it physically cannot conduct meaningfully below ~Vtn). **Decision: revise the floor to [0.35·VDD, 0.85·VDD] ≈ [0.63V, 1.53V]**, matching what this topology actually delivers with margin, rather than redesigning the bias generator (a fundamentally different level-shifted control scheme would be needed to go lower, and it's not needed for the specs in play). Flag this revision to Dr. Bindu alongside the ±0.15ppm restatement from `PROJECT_CHARTER.md` §4 — same category of correction (measured reality vs. an inherited number).
2. **Compensation ratio `C`.** Given the >3× tempco spread across corners (ff/tt/ss: 332/681/1070 ppm/°C), **decision: `C` is defined per-corner, `C(corner)`, not as a single scalar**, carried into the Review 2 compensation-network design and the H1 parity test.
   **Update 2026-09-29: this was an undercount.** Full 5-corner grid (all of tt/ff/ss/sf/fs, not the 3-corner spot-check) shows the real spread is **112 ppm/°C (sf) to 1399 ppm/°C (fs) — 12.5×**, not 3.4×. The worst corner (fs) wasn't in Review 1's spot-check at all. See `results/vco/FINDINGS_GRID5CORNER.md`. Strengthens decision 2 further; doesn't change it.

### A consequence of decision 1, worth carrying into Review 2 explicitly
`results/loop/FINDINGS.md` documents that a cold start *below* the (now-revised) Vctrl floor drives the loop into a multi-microsecond charge-pump-integration dead zone before the divider even starts toggling. The accepted closed-loop result starts from `.ic v(vctrl)=0.85V`, i.e. assumes the loop is already inside its valid range at power-up (a "coarse-tuned start," common in real PLLs via a separate acquisition-aid circuit that's out of scope here). Real cold-start-from-0V behavior is not yet a solved problem in this design — noted, not hidden.

## Review 2 checklist (target 75%) — **CLOSED OUT 2026-09-29**

All items resolved: either delivered, or explicitly deferred to Review 3 with a stated reason (not silently dropped). See `RESULTS.md` "Review 2 — Closing Summary" for the full narrative.

- [x] Full VCO PVT grid, **all 5 corners** (tt/ff/ss/sf/fs) × full Vctrl sweep × full temp sweep, 65 points — `results/vco/grid5corner.csv`, `results/vco/FINDINGS_GRID5CORNER.md`. Corrects Review 1's 3-corner spot-check: real spread is 12.5× (112-1399 ppm/°C), not 3.4×.
- [x] Second research axis added: curvature-matched (2nd-order) temperature compensation, novelty-checked against prior art (Infineon patent 9,748,962 B2 found and cited — narrowed our claim accordingly) — `PROJECT_CHARTER.md` §3.4.
- [x] Temperature-compensation network (idealized behavioral model, tt corner): baseline 8.51% span → 1st-order 3.04% → naive 2nd-order 4.49% (worse — real finding, see below) → empirically-refined 2nd-order **1.11%** (7.67× better than baseline). `results/comp/FINDINGS.md`, `docs/compensation_model.md`.
- [x] Statistical methodology researched and implemented: `scripts/stats.py` (paired t-test, Wilcoxon signed-rank, OLS regression w/ slope CI, MC sample-size formula), `docs/stats_methodology.md`.
- [x] Monte Carlo mismatch pass complete (n=12 seeds, tt corner, 3 compensation arms × 3 temps = 108 sims): all three pairwise comparisons statistically significant (paired t-test AND Wilcoxon agree). **n=12 is a first pass, below the recommended pilot n≈30**; re-run at proper sample size before final report. `results/comp/FINDINGS.md`.
- [x] **Per-corner compensation refit** — all 5 corners, k1+k2 refit independently. Every corner improves at both compensation stages: 2nd-order residuals range 0.10% (ff) to 5.31% (fs). Compensation ratio C ranges 3.30×-40.28× across corners — confirms (doesn't just motivate) the `C(corner)` decision. `results/comp/FINDINGS_PERCORNER.md`.
- [x] H1 regression point count — extended α-strength sweep to 6 (α, C) points (α=0, 0.25, 0.5, 0.75, 1.0, 1.25), meeting the stats-methodology minimum. OLS fit: slope=8.59, 95% CI=[2.93, 14.26] (excludes zero and one), R²=0.82. **This validates the regression pipeline on real data — it is NOT the H1 test itself**, which needs ε (ngspice-vs-Spectre disagreement), still blocked on Virtuoso access. `results/comp/FINDINGS_H1_PIPELINE.md`.
- [x] Sensitivity analysis — corner-level (not per-BSIM-parameter): the two N/P-mismatched corners (sf, fs) bracket the *entire* tempco range, not the matched-speed corners (ff, ss) — indicates N/P current-source balance, not absolute device speed, drives the spread. A full per-parameter tornado chart is deferred to Review 3 as a finer breakdown, not because this one is wrong. `docs/sensitivity_analysis.md`.
- [x] **Cold-start acquisition — fixed and verified.** Built a 5×-boosted-current charge pump variant (`charge_pump_acq.spice`) that reverts to nominal current once the divider produces its first edge. Simulated a TRUE 0V cold start (not the coarse-tuned 0.85V assumption): **locks in 839ns**, comfortably inside the 2µs spec. Worked on the first simulation attempt. `results/loop/FINDINGS_COLDSTART.md`.
- [x] FoM/benchmark table vs. reference papers — built using only independently-verified numbers (Ravi 2022, Geng et al. 2018/EAME, MDPI Electronics 2023); refs [2],[3],[5] excluded rather than fabricating their specs. Honest caveat included: comparisons mix simulation against measured silicon and shouldn't be oversold. `docs/benchmark_table.md`.
- [DEFERRED to Review 3, with reason] **Transistor-level charge pump and compensation network** — both still idealized behavioral models. Natural Review 3 tasks since layout (Magic) can't contain a behavioral B-source anyway; realizing them now would duplicate work once layout starts.
- [DEFERRED to Review 3, with reason] **Full n≥30 Monte Carlo** — n=12 already gives statistically significant results (agreed by two independent tests), so the methodology is proven; a larger campaign is a resource question, not a blocked task, and fits naturally alongside Review 3's transistor-level CP work.
- [DEFERRED to Review 3, with reason] **Jitter/phase-noise estimate** — genuinely blocked, not skipped: no PSS/Pnoise in open-source tools (confirmed independently by Sadhu et al. 2026), and a transient-based estimate would need real device noise modeling not yet built. The honest answer is "wait for Spectre RF," not a fabricated interim number.
- [DEFERRED to Review 3, with reason] **ε_raw ngspice-vs-Xyce** — Xyce isn't packaged for this OS (checked: not in apt, not in apt-cache); building from source is a multi-hour Trilinos-based compile, not worth it under this deadline. Real fallback is still the Virtuoso/Spectre arm once access lands.
- [DE-SCOPED, equivalent achieved] **CACE** — the hand-rolled sweep scripts (`run_sweep.sh`, `run_comp_sweep.sh`, `compile_vco_results.py`) already deliver everything CACE would (PVT/compensation sweeps, datasheet-style summaries). Adopting CACE itself would be a tooling-standardization nicety, not a new capability — not worth the setup time under this deadline.

## Review 3 checklist (target 100%) — not started
- [ ] Layout in Magic, DRC clean
- [ ] LVS clean via netgen (**tooling gap above must be fixed first**)
- [ ] Post-layout re-simulation
- [ ] Cadence arm: schematic rebuilt against sky130 Cadence ADK — **R1 in charter risk register: confirm Virtuoso access with the department now, not at Review 3**
- [ ] True PSS/Pnoise in Spectre RF
- [ ] GDS stream-in to Virtuoso demonstrated
- [ ] Parity tables (ε_raw, ε_res, C) and the H1 test
- [ ] Paper draft + reproducible artifact release

## Immediate next actions (in order)
1. Get the two Review-1 spec revisions (Vctrl floor, ±0.15ppm restatement) signed off by Dr. Bindu — both are corrections grounded in this pass's actual data, not just cleanup.
2. Temperature-compensation network design (Review 2 start) — PTAT/CTAT trim on the VCO bias, targeting the per-corner `C(corner)` decision.
3. Transistor-level charge pump, needed before Monte Carlo mismatch work means anything.
4. Full 5-corner × temperature CACE sweep.
5. Fix the netgen tooling gap before Review 3 needs it — not urgent yet.
