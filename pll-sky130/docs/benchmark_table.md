# Benchmark Against Reference Literature

Only comparing against papers where specific numbers were independently verified (not taken from memory or an abstract snippet) — see the inline citations. Refs [2], [3], [5] from `PROJECT_CHARTER.md` §13 are not included here because their exact quantitative specs weren't re-verified in this pass; listing invented numbers for them would be worse than leaving them out.

| Design | Process | Temp range | Residual tempco / stability | Lock time | Power |
|---|---|---|---|---|---|
| **This work — uncompensated** | sky130 (130nm) | -40 to 85°C | 112-1399 ppm/°C (corner-dependent) | 577 ns (tt, nominal) | ~58 µA @ 1.8V (VCO only) |
| **This work — 1st-order compensated** | sky130 (130nm) | -40 to 85°C | 0.42-9.13% span (corner-dependent, see below) | not yet re-measured closed-loop | same |
| **This work — 2nd-order refined** | sky130 (130nm) | -40 to 85°C | 1.11% span (tt, statistically significant vs 1st-order, n=12 MC) | not yet re-measured closed-loop | same |
| Ravi et al. 2022, *Microelectronics Journal* | 180nm CMOS | -40 to 120°C | -1.5%/+0.4% | not reported (VCO-only paper) | not reported |
| Geng et al. 2018 (EAME, ref [1]) | 180nm CMOS | 0 to 80°C | not directly comparable (freq-domain PLL, no ppm/°C reported) | **<2 µs** | 5mA @ 1.8V = **9 mW** |
| MDPI *Electronics* 12(3):507, 2023 (ref [4]) | not specified in abstract | not specified | **1.6%** temperature error (pre-layout, 50MHz) | n/a | n/a |

## Honest reading of this table

- Our **uncompensated** VCO's ppm/°C numbers look worse than the % numbers reported elsewhere because we're reporting a raw local slope (ppm/°C), not a %-over-range figure — apples-to-apples requires converting. Doing that: our tt corner uncompensated span is 8.51% over the full -40→85°C range, worse than Ravi's -1.5%/+0.4% (≈1.9% total) and worse than ref [4]'s 1.6% — **before compensation, we're behind published silicon, as expected** (we haven't compensated yet at that comparison point).
- After 2nd-order compensation (tt corner): **1.11%**, better than ref [4]'s 1.6%, and competitive with Ravi's ≈1.9% total swing — but Ravi's number is from fabricated silicon (measured), ours is from simulation (idealized behavioral compensation network, not yet transistor-level) — **not a like-for-like comparison yet**, and shouldn't be presented as beating published silicon until the transistor-level realization is measured the same way.
- Our lock time (577ns) comfortably beats ref [1]'s <2µs, but ref [1]'s number is also measured silicon at a much higher output frequency (2.1-2.6GHz vs our ≈226MHz) — again not strictly comparable without normalizing for frequency/technology.
- We do not have a phase-noise number to compare against ref [1]'s -117dBc/Hz@1MHz — this remains blocked on the lack of PSS/Pnoise in open-source tools (documented repeatedly, confirmed independently by Sadhu et al. 2026), deferred to Review 3's Spectre RF arm.

**Bottom line:** the compensation network is directionally competitive with published results on the one metric we can compare cleanly (residual % over range), but every comparison here mixes simulation against measured silicon, and the compensation network itself is still an idealized behavioral model. Don't oversell this table — it's evidence the approach is in the right ballpark, not proof of parity with fabricated designs.
