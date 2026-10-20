# Final compensation and Monte Carlo results (2026-10-20) -- supersede the Review-2 per-corner and MC numbers

All numbers: `results/final_numbers.md` (generated), `results/comp/factorial/factorial_comp_all.json`, `results/comp/mc_v2_analysis.txt`.

## What was wrong in Review 2
The Review-2 coefficients were limited by (a) the wrong K_VCO (669 instead of ~890 MHz/V) behind the analytic 1st-order coefficient (k1 = -2.163e-4), and (b) an empirical 2nd-order refit anchored to that. The 1st-order arm therefore over-corrected (tt span 3.05 %), and the Review-2 comparison "2nd order significantly better than 1st" was a comparison against a mis-tuned arm. The closed loop gave an independent hint: at tt the lock V_ctrl moves +11.9 mV (-40 C) and -7.5 mV (85 C) against the 27 C value, i.e. the required correction is +12 / -7.5 mV, while the old coefficients delivered +10.2 mV at -40 C.

## New method (`scripts/comp_factorial.py`)
Measure f(T, V) at V = 0.85 / 0.90 / 0.95 for -40, -20, 0, 27, 50, 85 C; solve the exact correction dV*(T) that restores f(27 C); least-squares fit k1 (1st order) and k1, k2 (2nd order); then verify by simulating the compensated VCO at the six fit temperatures and at four held-out temperatures (-30, 10, 40, 70 C).

## Results (nominal, ideal behavioural correction source)
tt: span 8.51 % -> 0.67 % (1st) -> 0.20 % (2nd); max deviation 0.162 % (spec +/-0.3 % met); held-out 0.091 %; k1 = -1.5426e-4 V/C, k2 = 4.1835e-7 V/C^2. Across 11 corners (9 textbook NMOS x PMOS + PDK sf/fs): 8 of 11 meet +/-0.3 % (nsps 0.277, ntps 0.195, ntpt 0.162, ntpf 0.168, nfps 0.079, nfpt 0.102, nfpf 0.093, PDK sf 0.051); not met: nspt 0.301 (borderline), nspf 0.325, PDK fs 0.360. Compensation ratio C = 31-44 (PDK sf 15.9, small baseline). The previous "met at ff and sf only (2 of 5)" is superseded.

## Monte Carlo (tt, mismatch on, paired by seed, |drift| = |f(85 C) - f(-40 C)|, n = 72)
Uncompensated 20.11 MHz [19.18, 21.04]; 1st order 3.25 [2.63, 3.87]; 2nd order 2.76 [2.33, 3.19]. Baseline -> 2nd: 17.35 MHz [16.37, 18.34], 72/72 chips. **1st vs 2nd order: 0.49 MHz, CI [-0.26, 1.24], not significant (paired t and Wilcoxon), 2nd smaller in 40/72 chips.** The residual (~3 MHz, 1.2-1.4 % of 226 MHz) is a mismatch floor: nominal residual is 0.2-0.7 %. A single global correction cannot remove chip-to-chip mismatch; a per-chip trim would be required to reach +/-0.3 % across chips. At n = 30 the same data gave 1.05 MHz [-0.14, 2.24], also not significant; n = 72 was chosen from a power calculation (SD of paired differences ~3.2 MHz -> n ~ 72 for 80 % power at 1.05 MHz).

## Caveats
Ideal source; two coefficients fitted to five temperature points (mitigated by the held-out check); fit at V_ctrl = 0.9 V while corners lock at 0.85-0.97 V (compensation should be defined at each corner's own lock voltage); the slow-NMOS corners are the hardest.
