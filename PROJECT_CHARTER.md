# Project Charter — Temperature-Compensated PLL in sky130, Open-Source Flow

**Status:** Locked as of 2026-08-27. Supersedes the tool/PDK choices in *Frequency Synthesizer Presentation.pdf* (Zeroth Review); preserves its objectives.

**Team:** Aaryan Dogra (23BEC1032), Yugeshwaran (23BEC1404), Viju Sanjai (23BEC1306)
**Guide:** Dr. B. Bindu, SENSE, VIT

**Purpose of this document:** prevent scope drift. Every decision below is settled. If we want to change one, we change it *here first*, with a dated entry in the Decision Log, rather than quietly drifting in the work.

---

## 1. The one-paragraph version

We design a temperature-compensated ring-oscillator PLL frequency synthesizer in the SkyWater sky130 open PDK using a fully open-source flow (Xschem → ngspice → CACE → Magic/KLayout → netgen), then cross-validate it against Cadence Virtuoso/Spectre on the same PDK. The circuit is the vehicle; the research contribution is the cross-validation. Specifically, we ask whether an open-source flow has enough model fidelity to design a **cancellation-based correction** — a problem class where two large temperature-dependent quantities are subtracted to leave a small residual, so that small model errors are amplified into large residual errors. We predict a measurable *trust ceiling* on how deep a correction an open-source flow can be relied upon to design, and we test that prediction quantitatively.

---

## 2. Locked problem statement

> Open-source analog EDA flows have been shown adequate for **first-order** design tasks — does the circuit function, does the oscillator run near the intended frequency. Temperature compensation is not a first-order task. It is a **cancellation** task: a correction network is designed so its temperature coefficient opposes and nearly cancels the oscillator's, leaving a residual one to two orders of magnitude smaller than either term. In such problems, model and simulator error do not pass through proportionally — they are amplified by roughly the compensation ratio. Whether open-source model fidelity survives that amplification is unknown and untested, and it determines whether open flows can be used for precision analog design at all, or only for functional prototyping.
>
> This project designs a temperature-compensated ring-VCO PLL in sky130 through a fully open-source flow, characterizes it across PVT and Monte Carlo mismatch, reproduces the identical testbenches in Cadence Virtuoso/Spectre on the same PDK, and quantifies how cross-flow disagreement propagates from raw quantities into the compensated residual — establishing an empirical bound on the correction depth an open-source flow can be trusted to design.

### 2.1 The falsifiable hypothesis

Let:
- `ε_raw` = relative cross-flow disagreement on directly simulated quantities (f_osc, K_VCO, I_bias, uncompensated tempco)
- `C` = compensation ratio = (uncompensated drift) / (compensated residual drift)
- `ε_res` = relative cross-flow disagreement on the *compensated residual* drift

**H1:** `ε_res ≈ C · ε_raw` — cross-flow error is amplified by the compensation ratio.

**Consequence if H1 holds:** an open-source flow cannot be trusted to design a correction deeper than `C_max ≈ 1/ε_raw`. If ngspice and Spectre agree on raw tempco to 3%, then compensation beyond ~30× is being designed on noise, and the "improvement" past that point is not physically meaningful.

Both outcomes are publishable:
- **H1 holds** → we deliver a concrete, quantified design rule for the open-silicon community, and a method for computing it in any other flow/PDK.
- **H1 fails** (error does *not* amplify) → stronger evidence for open-source precision-analog viability than anything currently published, and an interesting question about why the errors are correlated rather than independent.

Either way we have a result. This is the main reason to build the project around this question rather than around "did we hit ±X ppm".

---

## 3. Novelty analysis — honest version

### 3.1 What is NOT novel (do not claim these)

| Claim | Why it's not novel |
|---|---|
| A temperature-compensated ring VCO using PTAT bias current | Standard technique. [Souliotis et al., *AEU Int. J. Electron. Commun.* 2022](https://www.sciencedirect.com/science/article/abs/pii/S1434841122000929) fabricated exactly this in 180nm — PTAT-compensated ring VCO inside a PLL, −1.5%/+0.4% over −40→120°C. |
| A PLL in sky130 built with open-source tools | Already exists several times over — [ashokn414/apll_01v8_sky130](https://github.com/ashokn414/apll_01v8_sky130) (VSD internship), [TinyTapeout Tiny PLL](https://tinytapeout.com/chips/ttsky25a/tt_um_tiny_pll), and others. |
| A fully open-source PLL with an LC-VCO | Done — [Thiriloganathan et al., SMACD 2026](https://arxiv.org/html/2607.08852v1), 2.4 GHz fractional-N PLL in IHP SG13G2, Xschem/ngspice/KLayout/OpenEMS. |
| "Open-source EDA compares favourably to commercial tools" | Done for digital logic repeatedly, and partially for analog — see below. |

**We must state all of the above as prior art in the paper.** Claiming any of it as our contribution is how a reviewer kills the paper in one line.

### 3.2 The two closest works, and exactly what they leave open

**[Freitas et al., TWEPP 2025 / arXiv:2512.06122](https://arxiv.org/pdf/2512.06122)** — *Using Open Source EDA Tools in ASICs for HEP: A Mixed Comparison*. This is the closest prior work and we must cite it prominently.

- Compares open-source vs commercial in IHP SG13G2 across three blocks, one of which is **a differential current-starved ring-oscillator VCO** — very close to our analog benchmark.
- Methodology section promises matched models, stimuli and PVT corners across Xschem+ngspice and Virtuoso+Spectre.
- **But:** their Table 1 (digital) reports both flows side by side, while their **Table 2 (the VCO) reports the open-source flow only** — cell area, max oscillation frequency. There are *no published quantified open-vs-commercial analog numbers*. The analog comparison in the text is qualitative ("required more manual tuning", "slightly wider spread in oscillation metrics").
- The VCO is **standalone and open-loop**. No PLL, no closed loop.
- **No** temperature compensation. **No** Monte Carlo on the analog block. **No** phase noise or jitter.
- Stated future work: "expand to more blocks and include silicon measurements."

**[Thiriloganathan et al., SMACD 2026](https://arxiv.org/html/2607.08852v1)** — 2.4 GHz fractional-N LC-VCO PLL, IHP SG13G2, fully open-source.

- A complete open-source PLL, so the "can open tools build a PLL" question is answered.
- **No** temperature compensation, **no** PVT or Monte Carlo characterization, **no** comparison against commercial tools.
- Confirms independently that open tools lack direct phase-noise (PSS/Pnoise) analysis and that transient-based estimation is the accepted workaround.

### 3.3 The gap we occupy

The two closest works are complementary, and neither closes the gap:

```
                    open-vs-commercial      closed-loop      temperature      PVT +
                    QUANTIFIED analog       PLL              compensation     Monte Carlo
Freitas 2025            no (qualitative)     no               no               digital only
Thiriloganathan 2026              no                   yes              no               no
THIS PROJECT            yes                  yes              yes              yes
```

Our defensible novelty, stated precisely:

1. **First quantified open-source-vs-commercial parity study for a *closed-loop* analog system.** Freitas compares an open-loop VCO qualitatively. Closed-loop is a materially harder and more interesting test: loop dynamics (lock time, settling, phase margin, jitter peaking) compound simulator differences rather than averaging them out. Agreement on a free-running frequency does not imply agreement on a settling transient.
2. **First study to ask the cancellation-fidelity question at all.** Nobody has tested whether open-source model fidelity survives a subtraction-based correction. This is the actual intellectual contribution and the part that generalizes beyond PLLs — it applies to bandgap references, offset cancellation, any precision analog correction.
3. **A transferable methodology and metric** (the `C_max ≈ 1/ε_raw` trust ceiling) that any group can compute for their own flow/PDK/block.
4. Secondary: first temperature-compensated PLL characterized end-to-end in sky130 with published PVT + Monte Carlo data and a reproducible artifact.

Note that novelty #1–#3 do **not** depend on our compensation circuit being novel. This is deliberate and it is what makes the project safe: we are not betting the thesis on out-designing published silicon.

### 3.4 Second research axis: does curvature-matched compensation help, specifically here? (added 2026-09-29)

Review 1 measured that the VCO's uncompensated tempco is not constant — local slope varies 3.4× across -40→85°C (steeper cold, flatter hot; a concave curve, consistent with BSIM mobility/threshold temperature behavior). A standard first-order PTAT/CTAT network (Souliotis 2022, our own baseline) only cancels the linear component, leaving a curvature-shaped residual. This raised an obvious question: does adding a second-order (curvature-matched) term meaningfully reduce that residual, and is that worth the extra circuit complexity?

**Novelty check before committing to this as a headline claim (per standing practice — see memory: verify novelty before proposing research):** a dedicated research pass found **US Patent 9,748,962 B2 (Infineon Technologies AG, filed 2015, granted 2017), "Systems and methods for oscillators using quadratic temperature compensation."** It combines a linear PTAT term with a squared (quadratic) term via a translinear squarer, over the same -40→85°C range, explicitly stating "a linear temperature compensation may not compensate for second order temperature drift." **The general idea — add a quadratic term to a linear PTAT/CTAT compensator — is not novel and is patented.** We do not claim it. Curvature compensation is also decades-standard practice in bandgap references and temperature sensors (already excluded from our novelty claims in §3.1).

**What the same research pass confirmed is still open:** the Infineon patent is explicitly generic/non-PLL (it positions itself as a *lower-cost alternative to* PLL-based stabilization, and is exemplified at 24 GHz, almost certainly LC/varactor-tuned, not a ring oscillator). None of the published ring-oscillator temperature-compensation papers found (Souliotis 2022; Li/Du 2022; the 2022 IEEE ultra-low-power ring-osc paper; Zhang 2016) go past first order. No paper or patent found does curvature compensation of an oscillator in an open-source PDK — the closest adjacent effort (an open sky130 bandgap project) lists curvature correction as still-outstanding engineering work.

**Locked framing (narrow, defensible, composite):** we are not claiming "second-order VCO compensation" as novel. We claim: *quantifying, with statistical rigor (Monte Carlo + hypothesis testing, not a single spec number), whether a curvature-matched second-order network meaningfully outperforms first-order compensation, specifically for a ring-oscillator VCO inside a closed-loop PLL, in an open-source-simulated flow.* The composite (ring-VCO + closed-loop PLL + open PDK + statistically-validated quantification) is the unclaimed part, not the existence of quadratic compensation. Cite the Infineon patent in the related-work section of any writeup — a reviewer or examiner who knows this literature will find it if we don't cite it ourselves.

This axis is deliberately independent of the H1 cross-flow parity study (§2.1/§3.3): it produces a real, defensible result on its own even if Virtuoso access falls through, and it reuses the exact compensation-strength sweep (§9 risk R5) that H1 already needed for its (C, ε) regression — same simulation campaign serves both.

---

## 4. A technical correction to the Zeroth Review spec

**Raise this with Dr. Bindu before Review 1.** The PDF's headline target — "±0.15 ppm frequency stability across the temperature range" — is not physically meaningful as stated for a reference-locked PLL, and defending it in a review would be awkward.

In a PLL locked to an external reference, the output frequency is `f_out = N · f_ref` **exactly**. It is set by the reference and the divider ratio. Temperature does not change it while the loop stays locked — output ppm stability is inherited from the crystal reference, not from anything we design. So ±0.15 ppm is either trivially met (and measures the reference, not our circuit) or it is measuring something else.

What temperature *actually* degrades in a locked PLL, and what compensation actually buys:

| Real effect of temperature | Consequence | Our metric |
|---|---|---|
| VCO free-running frequency drifts | Required V_ctrl moves toward a rail → lock range shrinks → loss of lock | Residual free-running drift after compensation (%, ppm/°C) |
| K_VCO varies | Loop bandwidth and phase margin move → stability and jitter peaking change | K_VCO spread across temp; loop BW / phase margin vs temp |
| Startup/settling changes | Lock time varies | Lock time vs temp |
| Noise sources shift | Spectral purity degrades | Jitter / estimated phase noise vs temp |

**Proposed restatement of the target:**

- **Primary:** residual VCO free-running drift over −40→+85 °C reduced by ≥10× versus uncompensated. Published comparable silicon ([Souliotis 2022](https://www.sciencedirect.com/science/article/abs/pii/S1434841122000929)) achieves −1.5%/+0.4% in 180nm, so a target of **< ±0.3% (≈ ±24 ppm/°C)** is ambitious but grounded. `±0.15 ppm` is TCXO/crystal territory and is not achievable from a compensated ring oscillator.
- **Loop-level:** V_ctrl stays within **[0.35·VDD, 0.85·VDD] ≈ [0.63V, 1.53V]** across all corners and temperatures — *revised down from an original [0.15·VDD, 0.85·VDD] floor after simulation showed this ring-VCO topology is device-threshold-limited and is under 18 MHz below ~0.65V (originally written as "doesn't sustain oscillation below ~0.6-0.65V", which was a short-simulation-window artifact: there is no hard floor, corrected 2026-10-11); see decision log 2026-08-27 and 2026-10-11 and `pll-sky130/STATUS.md`*; lock time < 2 µs (keep from PDF, **confirmed achievable: 577ns measured at the nominal tt/27°C point with the original R2 = 1.7 kΩ; 503 ns after the 2026-10-11 retune to R2 = 3.6 kΩ, which also locks inside 2 µs at all five corners**, see `pll-sky130/results/loop/FINDINGS.md`); K_VCO variation < ±20% across temp.
- Keep phase noise < −80 dBc/Hz @ 10 kHz as a target, **explicitly labelled as transient-jitter-derived estimate**, not a PSS/Pnoise measurement.

This correction *strengthens* the review: it shows we understand what temperature does to a loop rather than copying a number. Frame it that way.

---

## 5. Alignment with the Zeroth Review PDF

Nothing in the approved objectives is abandoned. Traceability:

| PDF item | Status | Notes |
|---|---|---|
| Obj. 1 — Design a PLL-based CMOS synthesizer | **Kept** | Ring-VCO charge-pump PLL, sky130 instead of GPDK |
| Obj. 2 — Integrate temperature compensation | **Kept** | PTAT/CTAT bias correction on VCO control path; now also the vehicle for the research question |
| Obj. 3 — Simulate & verify in Cadence | **Kept, resequenced** | Open-source flow first, Cadence becomes the cross-validation arm (Review 3) |
| Obj. 4 — Benchmark against literature | **Kept, strengthened** | Now FoM-normalized, plus parity study against our own Cadence runs |
| Architecture: Ref → PFD → CP → LF → VCO → Divider | **Kept exactly** | Unchanged from PDF p.5 |
| −40 → +85 °C range | **Kept** | Unchanged |
| Lock time < 2 µs | **Kept** | Unchanged |
| Phase noise < −80 dBc/Hz @ 10 kHz | **Kept, relabelled** | Now explicitly an estimate on the open-source side |
| ±0.15 ppm stability | **Restated** | See §4 — technically incorrect as written |
| GPDK 45nm/180nm | **Replaced** | GPDK is NDA/licence-bound, cannot exist outside a Virtuoso seat → sky130 |
| "no physical layout" (PDF p.5) | **Expanded** | We now do full layout + DRC + LVS. Strictly more than promised. |
| Reviews 0–3 timeline | **Kept** | Mapped in §8 |

**Two things to tell Dr. Bindu explicitly:** (a) the PDK change is forced by licence availability, not preference, and sky130 is the one open PDK with a sanctioned Cadence path back; (b) we are *adding* layout, which the original scope excluded.

---

## 6. Locked decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **PDK: SkyWater sky130** | Only open PDK with an official Cadence ADK / Education Kit, which the parity study structurally requires. Silicon-proven, huge community. |
| D2 | **VCO: current-starved ring oscillator** (not LC) | Meets our spec without inductor models; keeps focus on the compensation/fidelity question; sky130 spiral-inductor coverage is thin. Also matches Freitas's benchmark, aiding comparability. |
| D3 | **Environment: IIC-OSIC-TOOLS Docker, pinned tag** | One image, all tools + PDKs, amd64/arm64, actively maintained by JKU. Pinning the tag is required for the reproducibility claim. |
| D4 | **Characterization: CACE** | Purpose-built for Xschem+ngspice PVT/Monte Carlo; produces datasheet-style output; it is our ADE Assembler replacement. |
| D5 | **Integer-N PLL, not fractional-N** | Fractional-N adds a ΔΣ modulator and quantization-noise analysis for zero benefit to the research question. Scope control. |
| D6 | **The parity study is the contribution; the circuit is the vehicle** | Protects us from being scooped on circuit design and from spec-chasing. |
| D7 | **Primary simulator ngspice; Xyce as independent cross-check** | Xyce is an independent codebase (Sandia), giving a second `ε` measurement and a fallback if Cadence access fails. |

---

## 7. Scope — in and out

### In scope
- Ring-VCO integer-N charge-pump PLL in sky130, full schematic hierarchy in Xschem
- PTAT/CTAT temperature-compensation network on the VCO bias
- Analytical loop model (loop BW, phase margin) verified against simulation
- PVT corner sweep + Monte Carlo mismatch via CACE
- Sensitivity / error-budget decomposition of residual drift
- Transient-jitter-derived phase-noise estimate
- Full layout: Magic (DRC, extraction), KLayout (GDS), netgen (LVS), post-layout sim
- Cadence Virtuoso/Spectre reproduction of identical testbenches; quantified parity
- FoM-normalized benchmark table against refs [1]–[5]
- Reproducible artifact: pinned image, all sources, one-command regeneration of every figure and table

### Explicitly OUT of scope (anti-drift list)
- ❌ Fractional-N / ΔΣ modulation
- ❌ LC-VCO, custom inductors, EM solving (OpenEMS)
- ❌ Tapeout, silicon, measured results
- ❌ Automated analog layout tools (ALIGN, MAGICAL)
- ❌ Digital flow, standard cells, OpenLane
- ❌ Supply/voltage compensation as a *design goal* (VDD stays a PVT sweep axis only)
- ❌ Beating published silicon on raw specs
- ❌ Any second PDK as a design target (IHP/GF180 only if a reviewer asks for generality, and only post-Review-3)

If work starts happening in the ❌ list, we have drifted. Come back to this document.

---

## 8. Milestones mapped to reviews

### Review 1 — target 50%
- [ ] IIC-OSIC-TOOLS running, tag pinned and recorded; sky130 verified
- [ ] Repo scaffold, directory structure, version control
- [ ] Block schematics in Xschem, each simulated standalone: PFD, charge pump, loop filter, ring VCO, divider
- [ ] VCO characterized: f_osc(V_ctrl), K_VCO, tuning range, supply current
- [ ] **Uncompensated** VCO temperature sweep — this is the baseline every later claim is measured against
- [ ] Closed loop assembled, lock demonstrated at nominal corner
- [ ] Analytical loop model derived by hand; predicted vs simulated loop BW and phase margin agree
- [ ] Literature/novelty section drafted (§3 of this document is the seed)

### Review 2 — target 75%
- [ ] Compensation network designed and integrated
- [ ] Compensated vs uncompensated drift; compensation ratio `C` measured
- [ ] Full PVT sweep via CACE, −40→+85 °C, all corners
- [ ] Monte Carlo mismatch: mean ± σ on residual drift, lock time, jitter
- [ ] Sensitivity / tornado analysis — which parameters drive residual drift
- [ ] Jitter-derived phase-noise estimate across temperature
- [ ] `ε_raw` measured **ngspice vs Xyce** (independent-codebase parity, and de-risks Review 3)
- [ ] FoM-normalized benchmark table vs refs [1]–[5]

### Review 3 — target 100%
- [ ] Layout in Magic, DRC clean; KLayout GDS export
- [ ] LVS clean via netgen against Xschem netlist
- [ ] Post-layout (extracted) re-simulation; compare to pre-layout
- [ ] **Cadence arm:** schematic rebuilt against sky130 Cadence ADK, identical testbenches, Spectre runs
- [ ] True PSS/Pnoise in Spectre RF — the one measurement open tools cannot make
- [ ] GDS stream-in to Virtuoso demonstrated
- [ ] **Parity tables:** `ε_raw`, `ε_res`, `C`, and the H1 test
- [ ] Trust-ceiling result stated: `C_max ≈ 1/ε_raw`
- [ ] Paper draft (SMACD / FOSSi / LASCAS-style workshop venue) + reproducible artifact released

---

## 9. Risks and fallbacks

| # | Risk | Severity | Mitigation / fallback |
|---|---|---|---|
| R1 | **No Cadence Virtuoso access materializes** — this is the premise of the whole project and the parity study needs it | **High** | Confirm access with Dr. Bindu / lab **before Review 1**, not at Review 3. Fallback: ngspice-vs-Xyce parity (independent codebases, same PDK models) still tests H1, just with a weaker second arm. Second fallback: compare against published silicon measurements from refs. The hypothesis survives both; only the strength of the claim drops. **This is the #1 risk — resolve it early.** |
| R2 | sky130 Cadence ADK not obtainable by our institution | Medium | Confirm alongside R1. Fallback: build a minimal Virtuoso-side model setup from open sky130 BSIM decks (models are the same silicon-calibrated decks; the ADK is packaging + symbols + layout rules). |
| R3 | No PSS/Pnoise in open tools | Medium | Known and already designed around: transient-jitter estimation, honestly labelled. This limitation is itself a *finding* we report, corroborated by Thiriloganathan 2026. |
| R4 | ngspice convergence problems on the closed loop | Medium | Xyce as alternate engine (D7); relax reltol, use `.ic`, staged startup. |
| R5 | Compensation ratio `C` too small to test H1 meaningfully | Medium | Need `C ≳ 10` for amplification to be visible above noise. If compensation underperforms, deliberately sweep compensation *strength* to generate a range of `C` values — this actually makes the H1 test **better** (a curve instead of a point). |
| R6 | Scope creep into layout automation / fractional-N / second PDK | Medium | §7 exists for exactly this. |
| R7 | Freitas et al. publish the quantified analog numbers in a v4 | Low-Medium | Would weaken novelty #1 but not #2 or #3 (cancellation fidelity, closed loop). Re-check arXiv before submission. |

---

## 10. Tool mapping (reference)

| Virtuoso component | Open-source replacement |
|---|---|
| Virtuoso Schematic Editor | Xschem |
| Spectre (tran/AC/DC) | ngspice (primary), Xyce (cross-check) |
| ADE Explorer | Xschem built-in simulate + gaw |
| ADE Assembler (corners, MC) | **CACE** |
| Spectre RF PSS/Pnoise | *No equivalent* — transient-jitter estimate; true measurement only in Review 3 Cadence arm |
| Virtuoso Layout Suite | Magic (DRC, extraction) + KLayout (GDS, viewing) |
| Assura / Calibre LVS | netgen |
| PDK | sky130A via open_pdks (open side) / sky130 Cadence ADK (commercial side) |

**Export paths back to Virtuoso:**
- **Layout → Virtuoso:** clean. GDSII/OASIS is native interchange; stream out from Magic/KLayout, Stream In to Virtuoso, with a layer map.
- **Schematic → Virtuoso:** no lossless converter (Xschem flat text vs. OpenAccess DB). The Xschem schematic + verified ngspice netlist is the **golden reference**; the Virtuoso schematic is rebuilt by hand against it. For the parity study this is *desirable* — an independent rebuild is a stronger test than a mechanical translation.

---

## 11. Decision log

| Date | Decision | Note |
|---|---|---|
| 2026-08-27 | GPDK → sky130 | Forced by licence availability; sky130 chosen over IHP SG13G2 / GF180 for its official Cadence ADK path |
| 2026-08-27 | Ring VCO over LC VCO | Spec doesn't need LC; avoids thin inductor-model coverage; keeps focus on research question |
| 2026-08-27 | Research framing set to cancellation-fidelity (H1) | After finding Freitas 2025 publishes no quantified analog parity numbers and Thiriloganathan 2026 has no temp comp / no commercial comparison |
| 2026-08-27 | ±0.15 ppm target flagged for restatement | Not physically meaningful for a reference-locked PLL — see §4. **Pending Dr. Bindu's approval.** |
| 2026-08-27 | Integer-N locked; fractional-N out of scope | Scope control |
| 2026-08-27 | VCO baseline simulated (rev1), adversarially critiqued, revised (rev2) | See `pll-sky130/results/vco/FINDINGS.md`. Real numbers: K_VCO ≈ 670 MHz/V (fit @ 0.9V, nonlinear curve) *[corrected 2026-10-11: local value ~890 MHz/V]*; uncompensated tempco +681 ppm/°C (tt secant), but +332 to +1070 ppm/°C across ff/ss — over 3× spread, meaning `C` likely needs to be per-corner, not scalar. **Open problem surfaced:** VCO does not sustain oscillation below Vctrl≈0.6-0.65V *[corrected 2026-10-11: it does oscillate, slowly; no hard floor, ~0.65V is the practical floor]*, contradicting the charter §4 floor of 0.27V — needs bias-generator resize or spec revision before Review 1 charge-pump/loop-filter work proceeds. |
| 2026-08-27 | V_ctrl lock-range floor revised: [0.27V,1.53V] → [0.63V,1.53V] | Device-threshold-limited (NMOS current source gate driven directly by Vctrl), not a sizing bug. *[2026-10-11: the 0.63V floor is a practical lock-range choice, not a measured oscillation cutoff; VCO is 18 MHz at 0.65V and sub-MHz at 0.5V.]* Redesigning for a lower floor needs a level-shifted control scheme, not justified by current specs. **Flag to Dr. Bindu** alongside the §4 ±0.15ppm restatement. |
| 2026-08-27 | Compensation ratio `C` locked as per-corner `C(corner)`, not scalar | Direct consequence of the >3× tempco spread (332/681/1070 ppm/°C across ff/tt/ss) found in the VCO baseline. Carries into Review 2 compensation-network design and the H1 parity test. |
| 2026-08-27 | Full PLL loop closed and locked (tt/27°C, single nominal point) | See `pll-sky130/results/loop/FINDINGS.md`. PFD (edge-detector + NOR SR-latch, not resettable DFFs — simpler, avoids fighting a TG-latch's own bistable loop), idealized behavioral charge pump (deliberate — transistor-level CP deferred to Review 2 where mismatch modeling is actually needed), passive loop filter sized from the analytical model in `docs/loop_model.md`, ÷8 transistor-level divider. **Lock time 577ns** (<2µs target; ~450ns analytical prediction, same order of magnitude *[2026-10-11: the 450 ns prediction was an arithmetic error and is withdrawn; 577 ns matches an independent averaged model, 573 ns. See the 2026-10-11 entry]*). Two real bugs found and fixed en route, both documented in FINDINGS.md: an inverted SPICE current-source node-order convention, and an inconsistent loop-filter capacitor `.ic` causing charge redistribution that was initially misdiagnosed as a digital cold-start glitch. **Open risk carried to Review 2:** a cold start below the (revised) Vctrl floor drives a multi-microsecond charge-pump acquisition dead zone; the accepted result assumes a coarse-tuned start. |
| 2026-09-29 | Full 5-corner grid run; tempco spread corrected to 12.5× (112-1399 ppm/°C), not the 3.4× from the 3-corner spot-check | `pll-sky130/results/vco/FINDINGS_GRID5CORNER.md`. fs corner (worst) wasn't in the original spot-check at all. |
| 2026-09-29 | Second research axis (curvature-matched compensation) added and novelty-checked before commitment | Found US Patent 9,748,962 B2 (Infineon, 2017) covers generic linear+quadratic oscillator compensation. Narrowed claim to the composite that's still open: ring-VCO + closed-loop PLL + open PDK + statistically-validated quantification. See §3.4. |
| 2026-09-29 | Review 2 closed out: per-corner compensation confirmed to generalize, cold-start acquisition fixed and verified (839ns from true 0V start, original R2 = 1.7 kΩ; 1352 ns after the 2026-10-11 retune), H1 regression pipeline validated on 6 real (α,C) points, sensitivity analysis and benchmark table delivered | `pll-sky130/RESULTS.md` "Review 2 — Closing Summary". Deferred to Review 3 with stated reasons: transistor-level CP/compensation network, n≥30 Monte Carlo, phase-noise estimate, Xyce cross-check (not packaged for this OS), CACE (hand-rolled scripts already equivalent). |
| 2026-09-29 | Self-review corrections before Review 2 | (1) MC compared *signed* drift, overstating 1st-vs-2nd at n=12; re-tested on \|drift\| and re-run at n=30 — 2nd-order now significantly better (−2.48 MHz, CI [0.81, 4.15]). (2) Per-corner fits were in-sample; validated at 4 held-out temperatures. (3) ±0.3% spec met at ff/sf only — now stated. (4) All 15 references verified by DOI: the ring-VCO baseline is **Souliotis et al.** (AEU 2022), not "Ravi"; the open-source LC PLL is **Thiriloganathan et al.** (SMACD 2026), not "Sadhu"; Freitas et al. is now in JINST. |
| 2026-10-11 | **Errata pass: four wrong claims corrected** (arithmetic, K_VCO, corner labels/mechanism, oscillation floor) | **What was wrong:** (1) `docs/loop_model.md` put K_VCO in rad/s/V into ωn² = Icp·Kvco/(N·C1) without the 1/(2π) of the PFD/CP gain; correct ωn² = Icp·Kvco_rad/(2π·N·C1). With R2=1.7k, C1=68p, Icp=20µA, N=8: fn ≈ 0.79 MHz, ζ ≈ 0.29 at K=669; fn ≈ 0.91 MHz, ζ ≈ 0.33, PM ≈ 30-33° at the measured K=887 MHz/V (Review 1 claimed 1.98 MHz, 0.72, 70-72°, BW 2.85 MHz, "450 ns"). The loop is underdamped. (2) K_VCO at 0.9V was ~887 MHz/V, not 669 (a quadratic fit over the whole S-shaped curve); per-corner sf 582 / ff 936 / tt 887 / ss 815 / fs 1018. (3) sf/fs were labelled backwards in the docs: sf = fast-NMOS/slow-PMOS, fs = slow-NMOS/fast-PMOS (PDK check); the "N/P current-source balance" tempco mechanism is replaced by NMOS overdrive (tempco ranks with NMOS Id at 0.9V; tt tempco flips to -816 ppm/°C at Vctrl=1.4V). (4) The "oscillation floor ≈0.63V" was a short-window artifact; the ring oscillates down to 0.5V (0.63 MHz), no hard floor. **How found:** an independent cross-check pass: `scripts/loop_check.py` (formulas plus an averaged behavioural loop model on the measured tuning curve), a fine K_VCO sweep (`results/vco/kvco_fine/`), long-window low-V_ctrl runs and a high-V_ctrl temperature run (`results/vco/floor_check/`), and a single-device PDK check. **What does NOT change (direct simulation results):** spans/tempcos (112/332/681/1070/1399 ppm/°C, 12.5×), 2nd-order spans, held-out checks, Monte Carlo statistics, lock times 577 ns (coarse) and 839 ns (0 V cold start), per-corner C values, tuning range 18 → 358 MHz, the empirically refit compensation coefficients. Measured 577 ns matches the independent averaged model (573 ns); the old "450 ns" agreement was coincidental. The analytic compensation k1/k2 used K=669, so overestimated the correction ~1.3×, a second reason (besides constant-K_VCO) the analytic 2nd-order network over-corrected. **Open (now CLOSED, same day, see the next row):** ~~retune R2 (≈3.6 kΩ for ζ≈0.7, not simulated) as a Review 3 item, with closed-loop tests re-run~~ — done and verified at transistor level. Spec (<2 µs lock) was met by the simulated runs of the original R2 = 1.7 kΩ design. |
| 2026-10-11 | **Loop filter retuned: R2 = 1.7 kΩ → 3.6 kΩ, verified by transistor-level simulation** (the "Retune R2" item is ticked; it was listed as a Review 3 task, now done) | **What:** R2 1.7 kΩ → 3.6 kΩ; C1 = 68 pF, C2 = 6.8 pF, Icp = 20 µA, N = 8, f_ref = 28.275 MHz unchanged. **Why:** with the corrected formulas and measured K_VCO = 887 MHz/V the original R2 gave ζ = 0.33 (PM ~30°, underdamped); R2 = 3.6 kΩ gives ζ ≈ 0.70 (PM ≈ 65-70°) at the same fn ≈ 0.91 MHz. **Evidence:** `pll-sky130/results/loop/retune/` (tt, coarse and 0 V cold start, R2 = 1.7k / 3.0k / 3.6k) and `results/loop/retune_corners/` (ss/ff/sf/fs, ss also at 5 µs); summary `results/loop/FINDINGS_RETUNE.md`. tt coarse start: lock 577 → 503 ns, final frequency error 0.78 % → 0.008 %, V_ctrl ripple 8.6 → 0.35 mV p-p. All five corners (coarse start) lock inside 2 µs with R2 = 3.6k: ff 241, sf 419, tt 503, fs 576, ss 967 ns; the original R2 = 1.7k loop had NOT finished settling within 2 µs at ff/sf/fs/ss. **Trade-off:** the true 0 V cold start is SLOWER, 839 → 1352 ns (+61 %), still inside the 2 µs spec; cold start simulated at tt only. Only R2 = 1.7k / 3.0k / 3.6k simulated at transistor level (plus an averaged-model sweep 1.7-6 k); 3.6k is not claimed optimal and R2 > 3.6k was not simulated. The ±2 % lock metric is sensitive at the band edge (503 ns is set by a 0.922 V overshoot just outside the 0.918 V band). **What is unchanged:** all open-loop results (tempcos, spans, compensation fits, held-out checks, Monte Carlo, K_VCO values, label corrections); they use the free-running VCO with an ideal control voltage. The 577 / 839 ns figures elsewhere in this document are the original R2 = 1.7 kΩ design. |
| 2026-10-20 | Final-review audit: compensation re-fit on the measured f(T,V) surface, Monte Carlo re-run at n = 72, textbook 3x3 corner set, closed-loop campaign over 11 corners | Review found corner values "out of range". Findings: PDK skew corners are wider than ss/ff (not inside the envelope); the Review-2 coefficients were mis-estimated through the K_VCO error (tt 0.87 % max dev -> 0.16 %); 2nd order is not significantly better than 1st once both are tuned (mismatch floor ~1.2-1.4 %); ss at 85 C cold start misses the 2 us spec by 4 % | `pll-sky130/results/final_numbers.md`, `results/corner_audit/FINDINGS.md`, `results/comp/FINDINGS_FINAL.md` |

---

## 12. Open questions to resolve before Review 1

1. **Does the department have Virtuoso access, and on what timeline?** (R1 — blocks the Review 3 arm; needs an answer now, not later.)
2. Can we obtain the sky130 Cadence Education Kit / ADK through VIT's Cadence relationship? (R2)
3. Does Dr. Bindu accept the §4 spec restatement?
4. Target output frequency and reference frequency — the PDF never fixes these. Proposal: f_ref = 10–50 MHz, f_out ≈ 1 GHz, N chosen accordingly; sky130 ring VCO at 1.8 V comfortably reaches ~1 GHz.
5. Target venue for the paper, which sets the page limit and the depth of the parity section.

---

## 13. References

**Prior art we position against:**
- É. M. V. Freitas et al., *Using Open Source EDA Tools in ASICs for HEP: A Mixed Comparison*, TWEPP 2025 / [arXiv:2512.06122](https://arxiv.org/pdf/2512.06122)
- *A 2.4 GHz LC-VCO Fractional-N Phase Locked Loop Open-Source Design in 130-nm BiCMOS*, SMACD 2026 / [arXiv:2607.08852](https://arxiv.org/html/2607.08852v1)
- *Temperature compensated ring oscillator based VCO*, [AEU Int. J. Electron. Commun., 2022](https://www.sciencedirect.com/science/article/abs/pii/S1434841122000929)
- [Working towards FOSS RF IC design in SKY130](https://wiki.f-si.org/index.php?title=Working_towards_FOSS_RF_IC_design_in_SKY130) — F-Si wiki

**Original deck references [1]–[5]:** retained, see *Frequency Synthesizer Presentation.pdf* p.9.

**Tooling:**
- [IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS) — JKU all-in-one container
- [CACE](https://github.com/efabless/cace) — Circuit Automatic Characterization Engine
- [open_pdks](https://github.com/rtimothyedwards/open_pdks) — sky130 PDK installer
- [SkyWater/Cadence open PDK announcement](https://www.skywatertechnology.com/skywater-announces-availability-of-cadence-open-source-pdk-and-reference-design-for-skywaters-130-nm-process/)
