# Status — Review 1 Progress Tracker

Last updated: 2026-10-11 (errata pass; original dates below are kept). Milestones per `PROJECT_CHARTER.md` §8. Update this file, don't let it drift from reality — if a checkbox is ticked, there's a file/result backing it.

## Errata (2026-10-11) — corrections to earlier claims in this repo

Found by independent re-checks (`scripts/loop_check.py`, `results/vco/kvco_fine/`, `results/vco/floor_check/`, PDK single-device check). Details in `docs/loop_model.md` and `PROJECT_CHARTER.md` decision log.
1. **Review-1 loop-filter arithmetic was wrong** (dropped the 1/(2π) PFD/CP gain). Corrected: fn ≈ 0.9 MHz (not 1.98), ζ ≈ 0.33 (not 0.72), phase margin ~30-33° (not 70-72°); the loop is underdamped. The "450 ns analytical prediction" is withdrawn. The measured 577 ns lock matches an independent averaged behavioural model (573 ns). **Retuned 2026-10-11 to R2 = 3.6 kΩ (ζ ≈ 0.70, PM ~65-70°) and verified by transistor-level simulation; see Review 2 errata item below.** The 577 ns / 839 ns figures in this file are the original R2 = 1.7 kΩ design.
2. **K_VCO at 0.9 V is ~890 MHz/V, not ~670** (per-corner: sf 580 / ff 940 / tt 890 / ss 820 / fs 1020).
3. **sf/fs corner labels were backwards.** sf = fast-NMOS / slow-PMOS; fs = slow-NMOS / fast-PMOS. The tempco mechanism is NMOS overdrive (tempco ranks with NMOS drive at 0.9 V), not "N/P current-source balance".
4. **"Oscillation floor 0.63 V" was wrong** (short-window artifact). The ring keeps oscillating subthreshold (0.5 V: 0.63 MHz, 0.6 V: 6.5 MHz, 0.65 V: 18 MHz). There is no hard floor; ~0.65 V is the practical floor for a usable VCO.
5. **Loop filter retuned (R2 1.7 kΩ → 3.6 kΩ) and verified, 2026-10-11** — see "Review 2 errata" checklist below and `results/loop/FINDINGS_RETUNE.md`.
6. **Unchanged:** spans/tempcos (112/332/681/1070/1399 ppm/°C, 12.5×), 2nd-order spans, held-out checks, Monte Carlo statistics, open-loop results (the retune only touches closed-loop numbers), per-corner C values, empirically refit compensation coefficients, tuning range 18 → 358 MHz. Closed-loop lock times 577 ns / 839 ns are the original R2 = 1.7 kΩ design (retuned: 503 / 1352 ns).

## Environment (done)
- [x] ngspice-42, Magic 8.3.105, KLayout 0.28.16 installed natively (apt), headless-capable
- [x] sky130 PDK (sky130B variant) pulled via volare, pinned to commit `c6d73a35f524070e85faff4a6a9eef49553ebc2b`
- [x] netgen — **built from source 2026-10-11** (the apt `netgen` is the wrong tool): `/home/pocopepe/tools/netgen/bin/netgen`, verified with the sky130B setup file on a test pair ("Circuits match uniquely"). Use the full path, `/usr/bin/netgen` is still the mesh generator. Install steps: `env/NETGEN.md`.
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
- [x] Closed loop assembled, lock demonstrated at nominal corner — `results/loop/FINDINGS.md`: **lock time 577ns with the original R2 = 1.7 kΩ** (target <2µs), settled within 0.85% of target frequency; **retuned loop (R2 = 3.6 kΩ): 503 ns, final frequency 0.008 % low, locks inside 2 µs at all five corners** (`results/loop/FINDINGS_RETUNE.md`) (the originally quoted "~450ns analytical prediction" was an arithmetic error, withdrawn 2026-10-11; see Errata)
- [x] Analytical loop model (loop BW, phase margin) derived and checked against sim — `docs/loop_model.md`. **Corrected 2026-10-11:** the Review-1 formula missed a 1/(2π); correct values for the original R2 = 1.7 kΩ are fn ≈ 0.9 MHz, ζ ≈ 0.33, PM ≈ 30-33° (underdamped); retuned R2 = 3.6 kΩ gives ζ ≈ 0.70, PM ≈ 65-70° (simulated, `docs/loop_model.md`). The measured 577 ns lock matches an independent averaged behavioural model (573 ns, `scripts/loop_check.py`); the earlier "450 ns" agreement was coincidental.
- [x] Literature/novelty section drafted — `PROJECT_CHARTER.md` §3

### Scoping decisions made getting here (both deliberate, both documented, neither hidden)
1. **Charge pump is an idealized behavioral model** (`Bcp` current source gated by UP/DN, no transistor switches, no mismatch, no charge injection). Standard PLL design sequencing: verify loop dynamics against the analytical model first with an ideal CP, harden to transistor-level once mismatch modeling is actually needed — which is Review 2 (Monte Carlo) anyway, so no wasted work.
2. **PFD built from edge-detectors + NOR SR-latches, not resettable D-flip-flops.** Considered the DFF+async-reset route first; adding a reliable async reset to a transmission-gate latch without fighting its own bistable feedback loop is genuinely fiddly, and the edge-detector/SR-latch structure is the standard textbook alternative that sidesteps the problem entirely. No loss of rigor — verified functionally the same way.

### The two decisions flagged in the previous update — now resolved
1. **V_ctrl lock-range floor.** Charter §4 originally specified [0.15·VDD, 0.85·VDD] = [0.27V, 1.53V]. Measured behaviour of this ring-VCO topology: frequency collapses below ~0.65V (device-threshold-limited: the NMOS current source's gate is driven directly by Vctrl, so it conducts very little below ~Vtn). *Corrected 2026-10-11: this was originally written as "minimum sustaining Vctrl ~0.6-0.65V", which was a short-simulation-window artifact; the ring keeps oscillating down to 0.5V and below, but at 0.63 MHz (0.5V), 2.1 MHz (0.55V), 6.5 MHz (0.6V), 18 MHz (0.65V) versus the 226 MHz target. No hard floor; ~0.65V is the practical floor.* **Decision: revise the floor to [0.35·VDD, 0.85·VDD] ≈ [0.63V, 1.53V]**, matching what this topology actually delivers with margin, rather than redesigning the bias generator (a fundamentally different level-shifted control scheme would be needed to go lower, and it's not needed for the specs in play). Flag this revision to Dr. Bindu alongside the ±0.15ppm restatement from `PROJECT_CHARTER.md` §4 — same category of correction (measured reality vs. an inherited number).
2. **Compensation ratio `C`.** Given the >3× tempco spread across corners (ff/tt/ss: 332/681/1070 ppm/°C), **decision: `C` is defined per-corner, `C(corner)`, not as a single scalar**, carried into the Review 2 compensation-network design and the H1 parity test.
   **Update 2026-09-29: this was an undercount.** Full 5-corner grid (all of tt/ff/ss/sf/fs, not the 3-corner spot-check) shows the real spread is **112 ppm/°C (sf) to 1399 ppm/°C (fs) — 12.5×**, not 3.4×. The worst corner (fs) wasn't in Review 1's spot-check at all. See `results/vco/FINDINGS_GRID5CORNER.md`. Strengthens decision 2 further; doesn't change it.

### A consequence of decision 1, worth carrying into Review 2 explicitly
`results/loop/FINDINGS.md` documents that a cold start *below* the (now-revised) Vctrl floor drives the loop into a multi-microsecond charge-pump-integration dead zone before the divider even starts toggling (below ~0.65 V the VCO is under 18 MHz, so the divided clock is effectively absent and the PFD sees only REF edges; the nominal 20 µA pump is too slow to climb out). The accepted closed-loop result starts from `.ic v(vctrl)=0.85V`, i.e. assumes the loop is already inside its valid range at power-up (a "coarse-tuned start," common in real PLLs via a separate acquisition-aid circuit that's out of scope here). Real cold-start-from-0V behavior is not yet a solved problem in this design — noted, not hidden.

## Review 2 checklist (target 75%) — **CLOSED OUT 2026-09-29**

All items resolved: either delivered, or explicitly deferred to Review 3 with a stated reason (not silently dropped). See `RESULTS.md` "Review 2 — Closing Summary" for the full narrative.

- [x] Full VCO PVT grid, **all 5 corners** (tt/ff/ss/sf/fs) × full Vctrl sweep × full temp sweep, 65 points — `results/vco/grid5corner.csv`, `results/vco/FINDINGS_GRID5CORNER.md`. Corrects Review 1's 3-corner spot-check: real spread is 12.5× (112-1399 ppm/°C), not 3.4×.
- [x] Second research axis added: curvature-matched (2nd-order) temperature compensation, novelty-checked against prior art (Infineon patent 9,748,962 B2 found and cited — narrowed our claim accordingly) — `PROJECT_CHARTER.md` §3.4.
- [x] Temperature-compensation network (idealized behavioral model, tt corner): baseline 8.51% span → 1st-order 3.04% → naive 2nd-order 4.49% (worse — real finding, see below) → empirically-refined 2nd-order **1.11%** (7.67× better than baseline). `results/comp/FINDINGS.md`, `docs/compensation_model.md`.
- [x] Statistical methodology researched and implemented: `scripts/stats.py` (paired t-test, Wilcoxon signed-rank, OLS regression w/ slope CI, MC sample-size formula), `docs/stats_methodology.md`.
- [x] Monte Carlo mismatch (tt, paired by seed, tested on |drift|): both compensation stages significantly reduce drift (n=12, 12/12 seeds each); 2nd-order significantly better than 1st-order at **n=30** (|drift| −2.48 MHz, 95% CI [0.81, 4.15], t-test and Wilcoxon agree, 23/30 seeds). A first analysis tested signed drift and overstated the 1st-vs-2nd result at n=12 — caught and corrected, see `docs/stats_methodology.md`. `results/comp/FINDINGS.md`.
- [x] **Per-corner compensation refit** — all 5 corners, every corner improves at both stages; 2nd-order span 0.10% (ff) to 5.31% (fs). Fits are in-sample, so each was re-checked at 4 held-out temperatures (−30/10/40/70°C) never used in fitting: held-out points stay inside the fitted envelope at every corner. **±0.3% spec met at ff and sf only** (tt 0.87%, ss 2.46%, fs 3.83% max deviation). `results/comp/FINDINGS_PERCORNER.md`.
- [x] Compensation-strength sweep: 6 (α, C) points generated, ready to pair with Spectre ε data for the H1 test. The α-vs-C fit itself is near-circular and carries no evidential weight. `results/comp/FINDINGS_H1_PIPELINE.md`.
- [x] Sensitivity analysis — corner-level (not per-BSIM-parameter): the two skew corners (sf = fast-NMOS/slow-PMOS, fs = slow-NMOS/fast-PMOS) bracket the *entire* tempco range. **Mechanism corrected 2026-10-11:** the earlier "N/P current-source balance" reading was wrong; the tempco ranks with NMOS drive at 0.9 V (sf 112 < ff 332 < tt 681 < ss 1070 < fs 1399 ppm/°C at NMOS Id 45.1/42.8/36.2/30.3/28.2 µA), because V_ctrl sets the NMOS starving current directly and less overdrive makes the Vth drop with T dominate. sf/fs bracket the range only because sky130's skew corners shift NMOS Vth by ±27 mV vs ±15 mV for ss/ff. An interpretation supported by ordering and a sign flip at V_ctrl=1.4 V (-816 ppm/°C), not an isolation experiment. A full per-parameter tornado chart is deferred to Review 3 as a finer breakdown, not because this one is wrong. `docs/sensitivity_analysis.md`.
- [x] **Cold-start acquisition — fixed and verified.** Built a 5×-boosted-current charge pump variant (`charge_pump_acq.spice`) that reverts to nominal current once the divider produces its first edge. Simulated a TRUE 0V cold start (not the coarse-tuned 0.85V assumption): **locks in 839ns with the original R2 = 1.7 kΩ** (1352 ns with the retuned R2 = 3.6 kΩ, slower but still inside the 2µs spec). Worked on the first simulation attempt. `results/loop/FINDINGS_COLDSTART.md`.
- [x] FoM/benchmark table vs. reference papers — built using only independently-verified numbers (Souliotis 2022, Stancu 2023, Geng 2018); all 15 deck references re-verified against publisher DOI records (several author/venue errors corrected). Honest caveat included: comparisons mix simulation against measured silicon and shouldn't be oversold. `docs/benchmark_table.md`.
- [x] **Review-2 erratum: loop filter retuned, R2 = 1.7 kΩ → 3.6 kΩ (2026-10-11), verified by transistor-level simulation.** ζ 0.33 → ~0.70, PM ~30 → ~65-70°, fn unchanged 0.91 MHz. tt coarse start: lock 577 → 503 ns, final frequency error 0.78 % → 0.008 %, V_ctrl ripple 8.6 → 0.35 mV p-p. tt 0 V cold start: 839 → **1352 ns (slower, +61 %)**, still < 2 µs. Five corners (coarse start): retuned loop locks in 241 / 419 / 576 / 503 / 967 ns at ff / sf / fs / tt / ss; the original loop had not settled by 2 µs at ff/sf/fs/ss. Only R2 = 1.7k / 3.0k / 3.6k simulated; not claimed optimal. Evidence: `results/loop/retune/` (tt, coarse + cold start), `results/loop/retune_corners/` (ss/ff/sf/fs, ss also at 5 µs), summary `results/loop/FINDINGS_RETUNE.md`, derivation `docs/loop_model.md`; testbenches `blocks/top/tb_closed_loop*.spice` now at r2=3.6k.
- [DEFERRED to Review 3, with reason] **Transistor-level charge pump and compensation network** — both still idealized behavioral models. Natural Review 3 tasks since layout (Magic) can't contain a behavioral B-source anyway; realizing them now would duplicate work once layout starts.
- [DEFERRED to Review 3, with reason] **Jitter/phase-noise estimate** — genuinely blocked, not skipped: no PSS/Pnoise in open-source tools (confirmed independently by Thiriloganathan et al. 2026), and a transient-based estimate would need real device noise modeling not yet built. The honest answer is "wait for Spectre RF," not a fabricated interim number.
- [DEFERRED to Review 3, with reason] **ε_raw ngspice-vs-Xyce** — Xyce isn't packaged for this OS (checked: not in apt, not in apt-cache); building from source is a multi-hour Trilinos-based compile, not worth it under this deadline. Real fallback is still the Virtuoso/Spectre arm once access lands.
- [DE-SCOPED, equivalent achieved] **CACE** — the hand-rolled sweep scripts (`run_sweep.sh`, `run_comp_sweep.sh`, `compile_vco_results.py`) already deliver everything CACE would (PVT/compensation sweeps, datasheet-style summaries). Adopting CACE itself would be a tooling-standardization nicety, not a new capability — not worth the setup time under this deadline.

## Review 3 checklist (target 100%) — not started
- [ ] Loop follow-ups after the R2 retune (which moved to the Review 2 checklist above as done): 0 V cold start at ff/sf/fs/ss (only tt simulated); re-check lock with the transistor-level charge pump when it exists.
- [ ] Layout in Magic, DRC clean
- [ ] LVS clean via netgen (tool now installed, see Environment)
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
5. (done 2026-10-11) netgen tooling gap fixed.
