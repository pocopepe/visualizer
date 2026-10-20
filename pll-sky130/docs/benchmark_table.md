# Benchmark Against Reference Literature

> **Superseded (2026-10-20):** the "This work" rows below use original Review-2 numbers (577 ns lock, 1.11 % tt span). Current: tt lock 503 ns coarse / 1351 ns cold start with R2 = 3.6 kOhm, re-fitted tt span 0.20 %; see results/final_numbers.md.

Only comparing against papers whose numbers were verified against the publisher record (DOI) — reference numbers match the Review-2 deck. Other references are omitted from this table because they measure different things (clock circuits, LC-VCO serial-link PLLs, GHz VCOs without compensation), not because their numbers are unknown.

| Design | Process | Temp range | Residual tempco / stability | Lock time | Power |
|---|---|---|---|---|---|
| **This work — uncompensated** | sky130 (130nm) | -40 to 85°C | 112-1399 ppm/°C (corner-dependent) | 577 ns (tt, nominal) | ~58 µA @ 1.8V (VCO only) |
| **This work — 1st-order compensated** | sky130 (130nm) | -40 to 85°C | 0.42-9.13% span (corner-dependent, see below) | not yet re-measured closed-loop | same |
| **This work — 2nd-order refined** | sky130 (130nm) | -40 to 85°C | 1.11% span (tt, nominal simulation; see `results/comp/FINDINGS.md` for the Monte Carlo significance result vs 1st-order) | 839 ns (true 0V cold start, tt) | same |
| Souliotis et al. 2022, AEU (ref [1]) | 180nm CMOS | -40 to 120°C | -1.5%/+0.4% (measured silicon) | not reported | not reported |
| Geng et al. 2018, EAME (ref [3]) | 180nm CMOS | 0 to 80°C | not directly comparable (freq-domain PLL, no ppm/°C reported) | **<2 µs** | 5mA @ 1.8V = **9 mW** |
| Stancu et al. 2023, Electronics (ref [2]) | simulation, 50 MHz clock circuit | not specified | **1.6%** temperature error (pre-layout, 50MHz) | n/a | n/a |

## Honest reading of this table

- Our **uncompensated** VCO's ppm/°C numbers look worse than the % numbers reported elsewhere because we're reporting a raw local slope (ppm/°C), not a %-over-range figure — apples-to-apples requires converting. Doing that: our tt corner uncompensated span is 8.51% over the full -40→85°C range, worse than Souliotis's -1.5%/+0.4% (≈1.9% total) and worse than ref [2]'s 1.6% — **before compensation, we're behind published silicon, as expected** (we haven't compensated yet at that comparison point).
- After 2nd-order compensation (tt corner): **1.11%**, better than ref [2]'s 1.6%, and competitive with Souliotis's ≈1.9% total swing — but Souliotis's number is from fabricated silicon (measured), ours is from simulation (idealized behavioral compensation network, not yet transistor-level) — **not a like-for-like comparison yet**, and shouldn't be presented as beating published silicon until the transistor-level realization is measured the same way.
- Our lock time (577ns) comfortably beats ref [3]'s <2µs, but ref [3]'s number is also measured silicon at a much higher output frequency (2.1-2.6GHz vs our ≈226MHz) — again not strictly comparable without normalizing for frequency/technology.
- We do not have a phase-noise number to compare against ref [3]'s -117dBc/Hz@1MHz — this remains blocked on the lack of PSS/Pnoise in open-source tools (documented repeatedly, confirmed independently by Thiriloganathan et al. 2026), deferred to Review 3's Spectre RF arm.

**Bottom line:** the compensation network is directionally competitive with published results on the one metric we can compare cleanly (residual % over range), but every comparison here mixes simulation against measured silicon, and the compensation network itself is still an idealized behavioral model. Don't oversell this table — it's evidence the approach is in the right ballpark, not proof of parity with fabricated designs.
