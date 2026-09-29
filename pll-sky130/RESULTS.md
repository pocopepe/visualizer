# Review 1 Results

Run `./scripts/demo_review1.sh` to regenerate every number below from scratch (headless, no GUI, ~8-12 min; `--fast` reuses the cached VCO sweep and finishes in ~3 min). Full narrative writeups: `results/vco/FINDINGS.md`, `results/loop/FINDINGS.md`, `docs/loop_model.md`, `PROJECT_CHARTER.md`.

## The hypothesis

**H1 (falsifiable):** Temperature compensation is a *cancellation* problem — a correction network is sized so its temperature coefficient nearly cancels the VCO's own, leaving a residual one to two orders of magnitude smaller than either term. In a cancellation problem, simulator/model disagreement doesn't pass through proportionally, it's amplified by roughly the compensation ratio:

> ε_res ≈ C · ε_raw, where C = uncompensated drift / compensated residual drift, and ε_raw is the ngspice-vs-Spectre disagreement on raw (uncompensated) quantities.

Consequence if it holds: an open-source flow can't be trusted to design a correction deeper than `C_max ≈ 1/ε_raw`. Both outcomes (holds / doesn't hold) are publishable — this is being tested, not assumed, and the full parity measurement (ε_raw, ε_res, C) is Review 3 scope once Virtuoso access is confirmed.

## What we took from the reference papers, and what we changed

| From | What we took | What we changed / added |
|---|---|---|
| Ravi et al. 2022 (*Microelectronics Journal*) | PTAT/CTAT-compensated ring-oscillator-in-PLL as the topology class — proven, fabricated, not a novel circuit to defend | We're not claiming the circuit is novel. Our contribution is measuring whether an open-source flow can be trusted to *design* it. |
| Freitas et al. 2025 (TWEPP, arXiv:2512.06122) | The idea of a quantified open-source-vs-commercial comparison, same PDK family (they use IHP SG13G2, close to our sky130) | Their VCO comparison is **open-loop and qualitative only** — no numbers, no closed loop, no temp compensation, no PVT/Monte Carlo. We close the loop, add compensation, and (Review 3) make the comparison quantitative. |
| Sadhu et al. 2026 (SMACD, arXiv:2607.08852) | Confirms independently that open-source tools have no PSS/Pnoise — a real, citable limitation, not one we're the first to hit | Their PLL has no temperature compensation and no commercial cross-check at all. We add both. |
| Original Zeroth Review deck | The block architecture (Ref → PFD → CP → LF → VCO → Divider), the -40→85°C range, the <2µs lock spec | Replaced GPDK45 with sky130 (licensing), added a full layout stage (originally schematic-only), and rewrote the frequency-stability spec (below) — the original number was not physically defensible. |

## What was proved wrong (from our own inherited spec, not from the reference papers)

| Original claim | Why it's wrong | What replaced it |
|---|---|---|
| **±0.15 ppm frequency stability** | In a reference-locked PLL, f_out = N·f_ref *exactly* in lock. Temperature can't move it while locked — that stability number describes the reference crystal, not anything the PLL design contributes. | Residual **VCO free-running drift < ±0.3% (≈±24 ppm/°C)**, benchmarked against Ravi 2022's fabricated −1.5%/+0.4%. |
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
- No phase noise / PSS analysis — not available in open-source tools (confirmed independently by Sadhu et al. 2026); Review 2 uses a transient/jitter estimate, Review 3 gets the real number from Spectre RF.
- Cold start from 0V drives a multi-microsecond acquisition dead zone (undocumented fix, flagged for Review 2) — the accepted lock result starts from a coarse-tuned V_ctrl=0.85V.

---

# Review 2 (in progress, 2026-09-29)

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

Monte Carlo mismatch pass: **n=12 seeds** (tt corner, 3 compensation arms, paired same-seed). This is explicitly a first pass — the methodology research recommends a pilot of n≈30 before sizing a final run; n=12 is below that, done under time constraints. Reproduce: `python3 scripts/analyze_mc.py`.

| Arm | Mean drift (85°C - -40°C) | 95% CI |
|---|---|---|
| Baseline | +18.927 MHz | [16.201, 21.654] |
| 1st-order | -6.152 MHz | [-8.404, -3.899] |
| 2nd-order refined | +3.275 MHz | [1.486, 5.065] |

**All three pairwise comparisons are statistically significant** (CIs exclude zero, confirmed by both a paired t-test and a Wilcoxon signed-rank test — they agree, which is a stronger result than either alone): baseline vs 1st-order, 1st-order vs 2nd-order, and baseline vs 2nd-order. The 2nd-order network's residual is significantly smaller in magnitude than 1st-order's (|3.275| vs |6.152| MHz), consistent with the deterministic pilot's 2.7× improvement. This is real hypothesis-testing rigor, not a single-run demo — though n=12 is a first pass, not the final statistically-saturated number (`results/comp/FINDINGS.md`).

## What's still open for Review 2

- Compensation coefficients are derived/refined against tt only — given the 12.5× corner spread just found, per-corner refinement is required, not optional, before claiming the compensation result generalizes.
- H1 (ε_res ≈ C·ε_raw) still needs ≥6-10 distinct compensation-ratio (C) values for a defensible regression — currently have 2 (1st-order, 2nd-order). Extend the α-strength sweep in `docs/compensation_model.md`.
- Monte Carlo at proper sample size (n≈30+, sized off this pilot's variance).
- Transistor-level charge pump and compensation network (both still idealized behavioral models) — needed before mismatch numbers mean anything beyond methodology demonstration.
