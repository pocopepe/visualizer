# Temperature-compensated PLL frequency synthesiser in open-source sky130

A final-year B.Tech project (VIT Chennai, School of Electronics Engineering): design and characterise an integer-N charge-pump PLL around a 5-stage current-starved ring VCO, measure how the VCO drifts with temperature across process corners, add a temperature-compensation correction, and validate it with statistics and closed-loop simulation. Everything is hand-written SPICE simulated with **ngspice** on the open **SkyWater sky130B** PDK, headless, no commercial tools.

## Status (honest)

Simulation-stage work, finished at the behavioural level. **Not done:** transistor-level charge pump and compensation network, layout, DRC, LVS, post-layout simulation, jitter / phase-noise numbers, and the commercial-tool (Spectre) cross-check. See [Known limitations](#known-limitations). Every number below is copied from [`pll-sky130/results/final_numbers.md`](pll-sky130/results/final_numbers.md), which is generated from the raw results by `pll-sky130/scripts/make_final_numbers.py`.

## What the design is

REF 28.275 MHz → PFD → charge pump (20 µA, 5× until the first divider edge) → loop filter (R2 = 3.6 kΩ, C1 = 68 pF, C2 = 6.8 pF) → 5-stage current-starved ring VCO → ÷8 → PFD. Target: 226.2 MHz at V_ctrl = 0.9 V (typical corner, 27 °C). Compensation adds `k1·(T−27) + k2·(T−27)²` to V_ctrl.

## Key results (11 process corners)

Corners are the 9 textbook NMOS × PMOS combinations (`nXpY`, X/Y ∈ s/t/f; `nsps` = ss, `ntpt` = tt, `nfpf` = ff exactly as in the PDK) plus the PDK's own skew corners `pdk_sf` (fast-NMOS / slow-PMOS in this PDK) and `pdk_fs` (slow-NMOS / fast-PMOS). Why both sets: the PDK's skew corners are wider than ss/ff and fall outside the ss–ff envelope at the VCO bias point; the 3×3 set is monotonic by construction ([`results/corner_audit/FINDINGS.md`](pll-sky130/results/corner_audit/FINDINGS.md)).

**Compensation: nominal, ideal behavioural correction source.** Span is (max − min)/f(27 °C) over −40…85 °C. **8 of 11 corners are within the ±0.3 % target**; `nspt` (0.301 %), `nspf` and `pdk_fs` are not.

| corner | uncompensated span % | 2nd-order span % | 2nd-order max dev % | held-out max dev % | meets ±0.3 % |
| --- | --- | --- | --- | --- | --- |
| nsps | 13.37 | 0.35 | 0.277 | 0.175 | yes |
| nspt | 13.97 | 0.38 | 0.301 | 0.201 | NO |
| nspf | 14.38 | 0.42 | 0.325 | 0.223 | NO |
| ntps | 8.10 | 0.24 | 0.195 | 0.109 | yes |
| ntpt | 8.51 | 0.20 | 0.162 | 0.091 | yes |
| ntpf | 8.79 | 0.20 | 0.168 | 0.097 | yes |
| nfps | 3.82 | 0.12 | 0.079 | 0.034 | yes |
| nfpt | 4.06 | 0.12 | 0.102 | 0.041 | yes |
| nfpf | 4.15 | 0.11 | 0.093 | 0.035 | yes |
| pdk_sf | 1.49 | 0.09 | 0.051 | 0.036 | yes |
| pdk_fs | 17.49 | 0.49 | 0.360 | 0.251 | NO |

**Closed loop (R2 = 3.6 kΩ), 27 °C.** Lock = V_ctrl within ±2 % of its final value; spec < 2000 ns. The VCO runs at 226.17 MHz (= 8 × f_ref) in every run.

| corner | lock, coarse start 0.85 V (ns) | lock, 0 V cold start (ns) | locked V_ctrl (V) |
|---|---|---|---|
| nsps | 966.8 | 1675.0 | 0.9678 |
| nspt | 645.3 | 1531.2 | 0.9437 |
| nspf | 572.8 | 1354.4 | 0.9305 |
| ntps | 677.5 | 1537.0 | 0.9198 |
| ntpt | 503.1 | 1351.4 | 0.9 |
| ntpf | 177.4 | 1318.1 | 0.8884 |
| nfps | 386.9 | 1390.8 | 0.8767 |
| nfpt | 279.1 | 1315.8 | 0.8597 |
| nfpf | 241.1 | 1282.5 | 0.8494 |
| pdk_sf | 419.3 | 1387.8 | 0.8694 |
| pdk_fs | 575.5 | 1355.1 | 0.942 |

**Temperature (cold start).** At the **ss corner and 85 °C the cold start misses the 2000 ns spec by about 4 %**:

| case (cold start) | lock (ns) |
|---|---|
| nsps_T-40_cold | 1632.8 |
| nsps_T27_cold | 1675.0 |
| nsps_T85_cold | 2082.7  **(misses the 2000 ns spec)** |
| ntpt_T-40_cold | 1318.5 |
| ntpt_T27_cold | 1351.4 |
| ntpt_T85_cold | 1417.8 |
| nfpf_T-40_cold | 1248.5 |
| nfpf_T27_cold | 1282.5 |
| nfpf_T85_cold | 1317.4 |

**Monte Carlo (typical corner, transistor mismatch on, 72 chips, paired by seed).** Both compensation networks cut the −40…85 °C drift from 20.1 MHz to 3.2 MHz (1st order) and 2.8 MHz (2nd order). **The 2nd-order network is *not* significantly better than the 1st-order one** (difference 0.49 MHz, 95 % CI [−0.26, 1.24], paired t-test and Wilcoxon not significant). The ~3 MHz (≈1.2–1.4 %) that remains is a chip-to-chip mismatch floor that a single global correction cannot remove.

## Known limitations

- The charge pump and the compensation network are **ideal behavioural models**, not transistors; the compensation result is nominal (no mismatch). With mismatch the residual is ≈1.2–1.4 %, so ±0.3 % across chips would need a per-chip trim.
- **No layout, DRC, LVS or post-layout simulation yet.**
- **No jitter / phase-noise number** (no PSS/Pnoise in the open tools used).
- Phase margin (≈65–70°) is the 100·ζ rule of thumb, not a Bode plot; only R2 = 1.7 / 3.0 / 3.6 kΩ were simulated, and 3.6 kΩ is not claimed optimal.
- 3 of 11 corners miss the compensation target; ss at 85 °C misses the lock-time spec.
- Quadratic temperature compensation itself is not novel (US 9,748,962 B2); the contribution is the closed-loop, per-corner, statistically validated study on an open PDK.
- Several earlier results were corrected during review (corner labels, K_VCO, loop damping, compensation coefficients, Monte Carlo conclusion); the history is kept in the errata sections of [`STATUS.md`](pll-sky130/STATUS.md) and [`PROJECT_CHARTER.md`](PROJECT_CHARTER.md).

## Quick start

```bash
cd pll-sky130
source env/pdk.env              # PDK_ROOT defaults to ~/pdk; see "Tools" below
./scripts/demo_review1.sh --fast
```

The demo re-simulates the VCO sweep, the PFD and divider checks and the closed loop and prints the reported-vs-measured numbers (typical corner: lock 503 ns, settled V_ctrl 0.900 V). On a fresh clone there is no cached sweep, so the first run executes the full sweep (about 10 minutes on 16 cores); later runs with `--fast` reuse it (about 4 minutes). Raw waveforms are not tracked; see [`pll-sky130/docs/REGENERATING.md`](pll-sky130/docs/REGENERATING.md) for how to regenerate every result set.

## Tools and PDK

- **ngspice 47** (all numbers were first produced with ngspice 42 and reproduce exactly), Python 3 with numpy, matplotlib and python-pptx, `pdflatex` (TikZ/circuitikz), LibreOffice (slide PDFs). netgen (IC-design LVS tool) can be built from source: [`pll-sky130/env/NETGEN.md`](pll-sky130/env/NETGEN.md).
- **sky130B PDK, pinned**: volare commit `c6d73a35f524070e85faff4a6a9eef49553ebc2b` (`export PDK_ROOT=/path/to/pdk`; `volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b`).
- `.spiceinit` sets one thread per ngspice process; the scripts run many processes in parallel.

## Repository map

```
README.md                     this file
PROJECT_CHARTER.md            goals, specs, risk register, decision log
HOW_TO_NAVIGATE.md            guided tour of the repo
pll-sky130/
  blocks/                     SPICE: vco/ pfd/ divider/ charge_pump/ loop_filter/ top/ (closed-loop testbenches)
  env/                        pdk.env (PDK location), NETGEN.md
  scripts/                    sweeps, analysis (stats.py, analyze_mc.py), campaign and figure/deck builders
  results/                    summaries (CSV/JSON/MD); results/final_numbers.md is the generated headline table
  docs/                       loop_model.md, compensation_model.md, stats_methodology.md, REGENERATING.md, LaTeX sources
    figures/ diagrams/        plots and circuit diagrams (TikZ sources + PNG)
    reviews/                  review decks, reading guides, reports and the final proposal (PDF/PPTX)
  RESULTS.md STATUS.md        narrative results and status/errata
```

## Citing / licence

No licence has been chosen yet. Until one is added, all rights are reserved by the authors.
