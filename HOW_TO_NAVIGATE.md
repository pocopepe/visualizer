# How to Navigate This Repo

New here? Read in this order:

1. **[cheatsheet.txt](pll-sky130/cheatsheet.txt)** — plain-language explainer of the whole project. Start here if you want the "what and why" without jargon.
2. **[PROJECT_CHARTER.md](PROJECT_CHARTER.md)** — the locked plan: research question, novelty analysis vs. published papers, scope, decisions, risks. This is the source of truth for *why* things are the way they are.
3. **[pll-sky130/RESULTS.md](pll-sky130/RESULTS.md)** — every number this project claims, the hypothesis, and what we proved wrong in our own inherited spec.
4. **[pll-sky130/STATUS.md](pll-sky130/STATUS.md)** — live progress tracker (Review 1 / 2 / 3 checklists). Check this to see what's actually done vs. planned.

## Directory layout

```
visualizer/
├── PROJECT_CHARTER.md          <- the plan, decisions, risk register (read first)
├── HOW_TO_NAVIGATE.md          <- this file
├── Frequency Synthesizer Presentation.pdf   <- original Zeroth Review deck (superseded scope-wise, kept for reference)
└── pll-sky130/                 <- all the actual work
    ├── cheatsheet.txt          <- plain-language explainer
    ├── RESULTS.md              <- all numbers + hypothesis + what changed
    ├── STATUS.md               <- progress tracker
    ├── env/pdk.env             <- source this before running anything: sets PDK paths
    ├── blocks/                 <- one subdirectory per circuit block, each with its .spice netlist
    │   ├── vco/                <- the oscillator (ring VCO)
    │   ├── pfd/                <- phase-frequency detector
    │   ├── charge_pump/        <- charge pump (idealized behavioral model, by design)
    │   ├── loop_filter/        <- passive RC loop filter
    │   ├── divider/            <- feedback divider (÷8)
    │   ├── digital/            <- shared logic-gate primitives (INV, NAND2, DFF, TFF, ...)
    │   └── top/                <- the assembled closed-loop testbench
    ├── scripts/                <- everything you run
    │   ├── demo_review1.sh     <- ONE COMMAND to regenerate every claimed result
    │   ├── run_sweep.sh        <- generic PVT/Vctrl sweep runner (used by the VCO sweep)
    │   ├── extract_freq.py     <- pulls oscillation frequency out of a transient waveform
    │   ├── compile_vco_results.py
    │   ├── verify_digital.py   <- checks PFD/divider functional correctness
    │   └── analyze_closed_loop.py
    ├── results/                <- simulation outputs + narrative findings
    │   ├── vco/FINDINGS.md     <- VCO characterization deep-dive
    │   └── loop/FINDINGS.md    <- closed-loop lock deep-dive (the two debugging stories)
    └── docs/
        ├── loop_model.md       <- the analytical loop-design math
        ├── reviews/review1_report.pdf  <- full 10-page Review 1 report
        ├── reviews/review1_summary.pdf <- 2-page faculty-facing summary
        └── diagrams/           <- circuit diagram sources (circuitikz/tikz) + rendered PNGs
```

## How to actually run something

```bash
cd pll-sky130
source env/pdk.env              # sets $PDK_ROOT, $SPICE_MODELS, etc.
./scripts/demo_review1.sh       # regenerates everything (~8-12 min)
./scripts/demo_review1.sh --fast   # reuses cached VCO sweep (~3 min)
```

Everything runs headless — no GUI, no Xschem, no Virtuoso. Netlists are plain SPICE text files, simulated with `ngspice -b`. See `cheatsheet.txt` for why.

## Requirements to build/run

- `ngspice` (simulator), `magic` + `klayout` (layout, Review 3+), all installed via `apt`
- SkyWater sky130 PDK via [`volare`](https://github.com/efabless/volare), pinned commit — see `pll-sky130/env/pdk.env`
- Python 3, no special packages beyond the standard library for the analysis scripts
- A working `pdflatex` + `circuitikz` if you want to rebuild the PDFs/diagrams in `docs/`

## Known gaps (see STATUS.md for the full list)

- `netgen` (LVS tool) isn't installed correctly yet — Ubuntu's package is a different tool with the same name. Needed for Review 3, not blocking yet.
- Charge pump is intentionally an idealized behavioral model until Review 2, where transistor-level mismatch actually starts to matter.
- Virtuoso/Cadence cross-validation (the other half of the research question) needs department access, not yet confirmed — see the risk register in `PROJECT_CHARTER.md`.
