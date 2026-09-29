# Review 1 Results

Run `./scripts/demo_review1.sh` to regenerate every number below from scratch (headless, no GUI, ~8-12 min; `--fast` reuses the cached VCO sweep and finishes in ~3 min). Full narrative writeups: `results/vco/FINDINGS.md`, `results/loop/FINDINGS.md`, `docs/loop_model.md`, `PROJECT_CHARTER.md`.

## The hypothesis

**H1 (falsifiable):** Temperature compensation is a *cancellation* problem — a correction network is sized so its temperature coefficient nearly cancels the VCO's own, leaving a residual one to two orders of magnitude smaller than either term. In a cancellation problem, simulator/model disagreement doesn't pass through proportionally, it's amplified by roughly the compensation ratio:

> ε_res ≈ C · ε_raw, where C = uncompensated drift / compensated residual drift, and ε_raw is the ngspice-vs-Spectre disagreement on raw (uncompensated) quantities.

Consequence if it holds: an open-source flow can't be trusted to design a correction deeper than `C_max ≈ 1/ε_raw`. Both outcomes (holds / doesn't hold) are publishable — this is being tested, not assumed, and the full parity measurement (ε_raw, ε_res, C) is Review 3 scope once Virtuoso access is confirmed.

## What we took from the reference papers, and what we changed

| From | What we took | What we changed / added |
|---|---|---|
| Souliotis et al. 2022 (*AEU Int. J. Electron. Commun.*) | PTAT/CTAT-compensated ring-oscillator-in-PLL as the topology class — proven, fabricated, not a novel circuit to defend | We're not claiming the circuit is novel. Our contribution is measuring whether an open-source flow can be trusted to *design* it. |
| Freitas et al. 2025 (TWEPP, arXiv:2512.06122) | The idea of a quantified open-source-vs-commercial comparison, same PDK family (they use IHP SG13G2, close to our sky130) | Their VCO comparison is **open-loop and qualitative only** — no numbers, no closed loop, no temp compensation, no PVT/Monte Carlo. We close the loop, add compensation, and (Review 3) make the comparison quantitative. |
| Thiriloganathan et al. 2026 (SMACD, arXiv:2607.08852) | Confirms independently that open-source tools have no PSS/Pnoise — a real, citable limitation, not one we're the first to hit | Their PLL has no temperature compensation and no commercial cross-check at all. We add both. |
| Original Zeroth Review deck | The block architecture (Ref → PFD → CP → LF → VCO → Divider), the -40→85°C range, the <2µs lock spec | Replaced GPDK45 with sky130 (licensing), added a full layout stage (originally schematic-only), and rewrote the frequency-stability spec (below) — the original number was not physically defensible. |

## What was proved wrong (from our own inherited spec, not from the reference papers)

| Original claim | Why it's wrong | What replaced it |
|---|---|---|
| **±0.15 ppm frequency stability** | In a reference-locked PLL, f_out = N·f_ref *exactly* in lock. Temperature can't move it while locked — that stability number describes the reference crystal, not anything the PLL design contributes. | Residual **VCO free-running drift < ±0.3% (≈±24 ppm/°C)**, benchmarked against Souliotis 2022's fabricated −1.5%/+0.4%. |
| **V_ctrl lock range [0.27V, 1.53V]** (0.15·VDD floor) | Measured: this ring-VCO topology doesn't sustain oscillation below ≈0.6–0.65V — it's device-threshold-limited (the NMOS current source's gate is driven directly by V_ctrl), not a sizing bug. | Floor revised to **[0.63V, 1.53V]** (0.35·VDD), matching what the topology actually delivers with margin. |
| *(implicit)* single scalar compensation ratio C | Measured tempco varies **>3× across corners** (332/681/1070 ppm/°C at ff/tt/ss) | **C locked as per-corner, C(corner)**, not scalar — carried into Review 2 compensation design. |

## All the numbers

### VCO (5-stage current-starved ring, sky130 nfet/pfet_01v8)

| Vctrl (tt, 27°C) | f_osc |
|---|---|
| 0.65 V | 18.0 MHz |
| 0.70 V | 41.3 MHz |
| 0.80 V | 125.2 MHz |
| 0.90 V | 226.2 MHz |
| 0.95 V | 266.1 MHz |
| 1.10 V | 324.1 MHz |
| 1.25 V | 346.0 MHz |
| 1.40 V | 358.1 MHz |

- **K_VCO ≈ 670 MHz/V** (fit derivative at 0.9V — curve is measurably nonlinear, don't quote a bare secant)
- **Uncompensated tempco:** ff **+332 ppm/°C**, tt **+681 ppm/°C**, ss **+1070 ppm/°C** (>3× spread)
- Per-interval tempco (tt, not a single number): +1123 → +924 → +722 → +537 → +352 ppm/°C, cold to hot
- **Minimum sustaining V_ctrl: ≈0.6–0.65V**

### PFD (edge-detector + NOR SR-latch)
- Functionally verified across a swept REF(20MHz)/DIV(18MHz) phase relationship
- UP pulse width 0.2–50.2 ns, DN 0.18–0.2 ns, tracking phase lead/lag correctly

### Divider (÷8, 3× toggle flip-flop)
- Measured ratio: **8.004** (target 8.000)

### Closed loop (tt, 27°C, nominal design point)

| Quantity | Measured | Target / Prediction |
|---|---|---|
| **Lock time** | **577 ns** | <2 µs (spec); 450 ns (analytical) |
| Settled V_ctrl | 0.902 V | 0.9 V design point |
| Settled divider frequency | 28.515 MHz | 28.275 MHz (0.85% high) |
| Settled VCO frequency | 227.96 MHz | 226.2 MHz (0.78% high) |

Loop filter: R2=1.7kΩ, C1=68pF, C2=6.8pF, Icp=20µA → predicted fn≈1.98MHz, ζ≈0.72, BW≈2.85MHz, PM≈70-72°.

## Two real bugs found and fixed (not cosmetic — both changed the result)

1. **SPICE current-source polarity**: ngspice's `B n1 n2 I=expr` draws current *out of* n1 when positive — backwards from the naive reading. Found via an isolated 4-line test, not by guessing against the full 3-minute loop sim.
2. **Inconsistent capacitor initial condition**: loop filter's internal node wasn't given an `.ic` matching vctrl's, so the two filter caps redistributed charge to ≈0.077V on startup. A 50ns charge-pump hold gate was added to test a (wrong) digital-glitch hypothesis first — the collapse *still happened inside that window*, which is what disproved the wrong hypothesis and pointed at the real cause.

## Known limitations, stated plainly

- Charge pump is an idealized behavioral model (no transistor switches, no mismatch) — deliberate, deferred to Review 2 where mismatch modeling is actually needed.
- Closed-loop lock is a single point (tt, 27°C) — full PVT sweep is Review 2.
- No phase noise / PSS analysis — not available in open-source tools (confirmed independently by Thiriloganathan et al. 2026); Review 2 uses a transient/jitter estimate, Review 3 gets the real number from Spectre RF.
- Cold start from 0V drives a multi-microsecond acquisition dead zone (undocumented fix, flagged for Review 2) — the accepted lock result starts from a coarse-tuned V_ctrl=0.85V.

---

# Review 2 (2026-09-29)

## Second research axis: does curvature-matched compensation actually help?

Novelty-checked before committing to this (see `PROJECT_CHARTER.md` §3.4): a 2017 Infineon patent (US 9,748,962 B2) already covers generic linear+quadratic oscillator compensation — **not novel on its own**. What's still open and is our actual claim: whether it's worth it *specifically for a ring-VCO inside a closed-loop PLL, in an open PDK*, quantified statistically rather than as a single spec number. The patent explicitly excludes the PLL case; no ring-oscillator paper found goes past first-order; no open-PDK implementation found.

### Compensation network results (tt corner, idealized behavioral model — see `docs/compensation_model.md`)

| Arm | Span, -40→85°C | vs baseline |
|---|---|---|
| Baseline (uncompensated) | 8.51% | — |
| 1st-order (PTAT/CTAT-equivalent) | 3.04% | 2.80× better |
| 2nd-order, naive analytically-derived k2 | 4.49% | **worse than 1st-order** |
| 2nd-order, empirically refined | **1.11%** | 7.67× better than baseline, 2.7× better than 1st-order |

**The naive-2nd-order-is-worse result is itself real, reportable content**, not noise: the small-signal derivation of the quadratic coefficient assumes constant K_VCO, which breaks down because K_VCO is itself measurably nonlinear (see the VCO tuning curve above). Refitting the coefficients against the *measured* post-1st-order residual (zero extra simulation — reused existing data) fixed it. Full writeup: `results/comp/FINDINGS.md`.

## Full 5-corner grid — corrects Review 1's spot-check

Review 1 only spot-checked 3 of 5 sky130 corners. All 5 now run (tt/ff/ss/**sf/fs**):

| Corner | Uncompensated tempco |
|---|---|
| sf | **+112 ppm/°C** |
| ff | +332 ppm/°C |
| tt | +681 ppm/°C |
| ss | +1070 ppm/°C |
| fs | **+1399 ppm/°C** |

**Real spread is 12.5× (112-1399 ppm/°C), not the 3.4× reported in Review 1** — the worst corner (fs) wasn't checked at all. Full data: `results/vco/FINDINGS_GRID5CORNER.md`, `results/vco/grid5corner.csv`.

## Statistical methodology (this is what "heavy hypothesis testing" means here)

No scipy in this environment — `scripts/stats.py` hand-rolls a paired t-test, Wilcoxon signed-rank (normal approximation), and OLS regression with a slope confidence interval, self-checked against known answers. Methodology sourced from a dedicated research pass, not invented ad hoc — see `docs/stats_methodology.md` for the reasoning (paired > unpaired given fixed SPICE seeds; report CI-excludes-zero instead of a p-value; regression needs ≥6-10 distinct points, not 3-4).

Monte Carlo mismatch (tt, arms paired by seed, tested on **|drift|** — the quantity that means "better"). Reproduce: `python3 scripts/analyze_mc.py`.

| Arm | n | Mean \|drift\|, 85°C vs −40°C | 95% CI |
|---|---|---|---|
| Baseline | 12 | 18.93 MHz (8.4%) | [16.20, 21.65] |
| 1st-order | 30 | 5.86 MHz (2.6%) | [4.62, 7.09] |
| 2nd-order refined | 30 | 3.37 MHz (1.5%) | [2.33, 4.41] |

- Both compensation stages significantly reduce drift (12/12 seeds each, t-test and Wilcoxon agree).
- **2nd-order is significantly better than 1st-order at n=30:** |drift| −2.48 MHz, 95% CI [0.81, 4.15], both tests agree, 23/30 seeds.
- **Correction on record:** the first analysis tested *signed* drift and called 1st-vs-2nd significant at n=12 — mostly because 1st-order over-corrects (negative) and 2nd-order doesn't. On |drift| at n=12 it was *not* significant. The n=30 re-run is what earns the claim. See `docs/stats_methodology.md`.

---

# Review 2 — Closing Summary (2026-09-29)

Every checklist item resolved: delivered, or explicitly deferred to Review 3 with a stated reason. Full item-by-item status: `STATUS.md`.

## Delivered

- **Per-corner compensation generalizes.** All 5 corners refit independently: every corner improves at both stages; 2nd-order span 0.10% (ff) to 5.31% (fs); C spans 3.30×-40.28×. The fits are in-sample, so each was re-checked at 4 held-out temperatures never used in fitting — all held-out points stay inside the fitted envelope. `results/comp/FINDINGS_PERCORNER.md`.
- **Against our own ±0.3% spec: met at ff (0.07%) and sf (0.15%) only.** tt 0.87%, ss 2.46%, fs 3.83% max deviation from 27°C. Closing this is Review-3 work (process-tracking transistor-level network and/or per-corner trim).
- **2nd-order beats 1st-order under mismatch** — significant at n=30 on |drift| (see above).
- **Cold-start acquisition — fixed and verified.** A 5×-boosted-current charge pump variant closes the multi-microsecond dead-zone risk flagged since Review 1. Simulated from a TRUE 0V cold start (not the coarse-tuned 0.85V assumption): **locks in 839ns**, inside the 2µs spec, on the first attempt. `results/loop/FINDINGS_COLDSTART.md`.
- **Compensation-strength sweep** — 6 (α, C) points ready to pair with Spectre ε data for the H1 test. The α-vs-C fit is near-circular and isn't evidence of anything by itself. `results/comp/FINDINGS_H1_PIPELINE.md`.
- **Sensitivity insight** from existing corner data (no new sims): N/P-mismatched corners (sf, fs) — not absolute device speed — bracket the entire tempco range, pointing at current-source balance as the mechanism. `docs/sensitivity_analysis.md`.
- **Benchmark table** against 3 references whose numbers were checked against publisher records; all 15 deck references re-verified by DOI (corrected several author/venue errors, e.g. the ring-VCO baseline paper is Souliotis et al., AEU). `docs/benchmark_table.md`.

## Deferred to Review 3, with reasons (not silently dropped)

| Item | Why deferred |
|---|---|
| Transistor-level charge pump + compensation network | Both still idealized behavioral models; natural Review 3 work since layout (Magic) needs real transistors anyway |
| Monte Carlo at other corners | tt only so far; the spec gap at ss/fs is the priority before more MC |
| Jitter/phase-noise estimate | Genuinely blocked: no PSS/Pnoise in open-source tools (independently confirmed by Thiriloganathan et al. 2026); a fabricated interim number would be worse than waiting for Spectre RF |
| ε_raw ngspice-vs-Xyce | Xyce isn't packaged for this OS; building from source is a multi-hour compile, not worth it under this deadline |
| CACE | Hand-rolled sweep scripts already deliver the same capability; adopting CACE itself is a tooling nicety, not a new result |
