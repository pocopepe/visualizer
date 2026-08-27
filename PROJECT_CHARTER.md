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
| A temperature-compensated ring VCO using PTAT bias current | Standard technique. [Ravi et al., *Microelectronics Journal* 2022](https://www.sciencedirect.com/science/article/abs/pii/S1434841122000929) fabricated exactly this in 180nm — PTAT-compensated ring VCO inside a PLL, −1.5%/+0.4% over −40→120°C. |
| A PLL in sky130 built with open-source tools | Already exists several times over — [ashokn414/apll_01v8_sky130](https://github.com/ashokn414/apll_01v8_sky130) (VSD internship), [TinyTapeout Tiny PLL](https://tinytapeout.com/chips/ttsky25a/tt_um_tiny_pll), and others. |
| A fully open-source PLL with an LC-VCO | Done — [Sadhu et al., SMACD 2026](https://arxiv.org/html/2607.08852v1), 2.4 GHz fractional-N PLL in IHP SG13G2, Xschem/ngspice/KLayout/OpenEMS. |
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

**[Sadhu et al., SMACD 2026](https://arxiv.org/html/2607.08852v1)** — 2.4 GHz fractional-N LC-VCO PLL, IHP SG13G2, fully open-source.

- A complete open-source PLL, so the "can open tools build a PLL" question is answered.
- **No** temperature compensation, **no** PVT or Monte Carlo characterization, **no** comparison against commercial tools.
- Confirms independently that open tools lack direct phase-noise (PSS/Pnoise) analysis and that transient-based estimation is the accepted workaround.

### 3.3 The gap we occupy

The two closest works are complementary, and neither closes the gap:

```
                    open-vs-commercial      closed-loop      temperature      PVT +
                    QUANTIFIED analog       PLL              compensation     Monte Carlo
Freitas 2025            no (qualitative)     no               no               digital only
Sadhu 2026              no                   yes              no               no
THIS PROJECT            yes                  yes              yes              yes
```

Our defensible novelty, stated precisely:

1. **First quantified open-source-vs-commercial parity study for a *closed-loop* analog system.** Freitas compares an open-loop VCO qualitatively. Closed-loop is a materially harder and more interesting test: loop dynamics (lock time, settling, phase margin, jitter peaking) compound simulator differences rather than averaging them out. Agreement on a free-running frequency does not imply agreement on a settling transient.
2. **First study to ask the cancellation-fidelity question at all.** Nobody has tested whether open-source model fidelity survives a subtraction-based correction. This is the actual intellectual contribution and the part that generalizes beyond PLLs — it applies to bandgap references, offset cancellation, any precision analog correction.
3. **A transferable methodology and metric** (the `C_max ≈ 1/ε_raw` trust ceiling) that any group can compute for their own flow/PDK/block.
4. Secondary: first temperature-compensated PLL characterized end-to-end in sky130 with published PVT + Monte Carlo data and a reproducible artifact.

Note that novelty #1–#3 do **not** depend on our compensation circuit being novel. This is deliberate and it is what makes the project safe: we are not betting the thesis on out-designing published silicon.

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

- **Primary:** residual VCO free-running drift over −40→+85 °C reduced by ≥10× versus uncompensated. Published comparable silicon ([Ravi 2022](https://www.sciencedirect.com/science/article/abs/pii/S1434841122000929)) achieves −1.5%/+0.4% in 180nm, so a target of **< ±0.3% (≈ ±24 ppm/°C)** is ambitious but grounded. `±0.15 ppm` is TCXO/crystal territory and is not achievable from a compensated ring oscillator.
- **Loop-level:** V_ctrl stays within [0.15·VDD, 0.85·VDD] across all corners and temperatures; lock time < 2 µs (keep from PDF); K_VCO variation < ±20% across temp.
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
| R3 | No PSS/Pnoise in open tools | Medium | Known and already designed around: transient-jitter estimation, honestly labelled. This limitation is itself a *finding* we report, corroborated by Sadhu 2026. |
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
| 2026-08-27 | Research framing set to cancellation-fidelity (H1) | After finding Freitas 2025 publishes no quantified analog parity numbers and Sadhu 2026 has no temp comp / no commercial comparison |
| 2026-08-27 | ±0.15 ppm target flagged for restatement | Not physically meaningful for a reference-locked PLL — see §4. **Pending Dr. Bindu's approval.** |
| 2026-08-27 | Integer-N locked; fractional-N out of scope | Scope control |
| 2026-08-27 | VCO baseline simulated (rev1), adversarially critiqued, revised (rev2) | See `pll-sky130/results/vco/FINDINGS.md`. Real numbers: K_VCO ≈ 670 MHz/V (fit @ 0.9V, nonlinear curve); uncompensated tempco +681 ppm/°C (tt secant), but +332 to +1070 ppm/°C across ff/ss — over 3× spread, meaning `C` likely needs to be per-corner, not scalar. **Open problem surfaced:** VCO does not sustain oscillation below Vctrl≈0.6-0.65V, contradicting the charter §4 floor of 0.27V — needs bias-generator resize or spec revision before Review 1 charge-pump/loop-filter work proceeds. |

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
- *Temperature compensated ring oscillator based VCO*, [Microelectronics Journal, 2022](https://www.sciencedirect.com/science/article/abs/pii/S1434841122000929)
- [Working towards FOSS RF IC design in SKY130](https://wiki.f-si.org/index.php?title=Working_towards_FOSS_RF_IC_design_in_SKY130) — F-Si wiki

**Original deck references [1]–[5]:** retained, see *Frequency Synthesizer Presentation.pdf* p.9.

**Tooling:**
- [IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS) — JKU all-in-one container
- [CACE](https://github.com/efabless/cace) — Circuit Automatic Characterization Engine
- [open_pdks](https://github.com/rtimothyedwards/open_pdks) — sky130 PDK installer
- [SkyWater/Cadence open PDK announcement](https://www.skywatertechnology.com/skywater-announces-availability-of-cadence-open-source-pdk-and-reference-design-for-skywaters-130-nm-process/)
