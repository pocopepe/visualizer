# Compensation Network — Coefficient Derivation

Idealized model (see `blocks/vco/tb_comp_template.spice`): a correction voltage in series with Vctrl,

    vctrl_eff = vctrl_nom + k1*(T-27) + k2*(T-27)^2

`k1` cancels the linear component of drift, `k2` additionally cancels the curvature Review 1 measured (local tempco slope varies 3.4x across -40..85C, not constant — see `results/vco/FINDINGS.md`). Setting `k2=0` gives standard first-order (PTAT/CTAT-equivalent) compensation; `k2≠0` is the curvature-matched second-order network.

## From measured data to k1, k2

Review 1's fit (tt corner, Vctrl=0.9V): `f(T) = 221.7 + 0.1919*T - 0.00087*T^2` [MHz]. Rewriting around T=27 (ΔT = T-27):

    f(T) = f(27) + b1*ΔT + b2*ΔT^2
    b1 = a1 + 54*a2 = 0.1919 + 54*(-0.00087) = 0.14492 MHz/C
    b2 = a2 = -0.00087 MHz/C^2

To cancel drift via K_VCO: ΔVctrl(T) = -Δf(T)/K_VCO. The derivation as originally done used K_VCO = 669 MHz/V (Review 1 quadratic fit), giving:

    k1_full = -b1/K_VCO = -2.163e-4  V/C
    k2_full = +1.299e-6  V/C^2

> **Erratum (2026-10-11).** 669 MHz/V was the wrong K_VCO for this purpose. The local derivative at 0.9 V (tt, 27 °C, fine sweep, `results/vco/kvco_fine/`) is **887 MHz/V**; with it the analytic coefficients would be ≈ -1.63e-4 V/C and ≈ +0.98e-6 V/C^2 (scaled by 669/887). So the analytic coefficients were ~1.3× too large. This is a **second reason**, besides the constant-K_VCO assumption (K_VCO changes along the V_ctrl excursion), why the analytic 2nd-order network over-corrected (`results/comp/FINDINGS.md`). The coefficients actually used in the simulations are the empirically refit ones (fit directly to simulated residuals), as are the spans, held-out checks and Monte Carlo statistics; none of those depend on the 669 figure and they are unchanged.

## Compensation-strength sweep (for the H1 regression, paired with cross-flow ε once Virtuoso access lands)

Coefficients scaled by strength α: `k1 = α*k1_full`, `k2 = α*k2_full` (curvature arm) or `k2=0` (linear-only arm). α ∈ {0, 0.5, 1.0, 1.5} gives 4 compensation ratios C per arm for a pilot fit; point count needed for a defensible regression slope CI is TBD pending the statistical-methodology research pass (see `docs/stats_methodology.md` once written) — extend the α grid once that lands.

`C` (compensation ratio) = uncompensated drift / compensated residual drift, computed per corner from the sweep output.
