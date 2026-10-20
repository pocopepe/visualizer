# Corner audit (2026-10-20): do the sky130 corner numbers follow textbook ordering? If not, why?

Raised in review: ff / tt / fs / sf values "aren't in the ranges they're meant to be". Everything below is measured (ngspice 47, `libs.tech/ngspice/sky130.lib.spice`, sky130B, volare c6d73a35...; ngspice 47 reproduces the earlier ngspice-42 results exactly: tt, 27 C, 0.9 V = 226.206 MHz). Scripts: `scripts/corner_audit.py` (devices), `scripts/make_factorial_lib.py` (textbook 3x3 corner library), `scripts/factorial_analysis.py` (ordering checks). Raw numbers: `results/final_numbers.md`, `results/corner_audit/device_corners.csv`, `results/vco/factorial.csv`.

## Verdict
Nothing in the simulations was broken. Three things were wrong in how we **expected and described** the corners:
1. **Labels.** In this PDK `sf` is fast-NMOS / slow-PMOS and `fs` is slow-NMOS / fast-PMOS (behaviour, measured; the PDK only says "Slow-Fast corner (sf)" without naming devices, and the SkyWater doc tables are internally inconsistent about it, so we do not rely on them). Fixed earlier (errata).
2. **Expectation.** "Skew corners lie between ss and ff" is false for this PDK. Its skew corners shift each device further than ss/ff do. Extracted NMOS Vth shift vs tt: ss +25 mV, ff -25 mV, **sf -36 mV, fs +36 mV**; PMOS |Vth|: ss +15, ff -23, **sf +32, fs -43 mV**. At the VCO bias (|Vgs| = 0.9 V, overdrive only ~0.2-0.25 V) an extra ~11 mV of Vth is ~2*11/230 = ~9 % of drive current: NMOS Id at 0.9 V is fs 25.3 < ss 27.9 < tt 36.9 < ff 47.7 < sf 51.3 uA, i.e. the skews fall outside the ss-ff envelope by 8-9 %. At 1.8 V the same corners are inside to within 1 % (ss 401, fs 397, tt 438, ff 475, sf 480 uA). So the "out of range" values are a low-overdrive amplification of a wider-than-symmetric PDK corner definition.
3. **Tempco is not bounded by ff and ss in any corner set.** With NMOS and PMOS varying independently, tempco extremes occur at the skew corners even in a clean textbook set: textbook 3x3 range 306-1151 ppm/C (3.8x), PDK sf/fs 112-1399 (12.5x).

## The textbook 3x3 factorial set (NMOS slow/typ/fast x PMOS slow/typ/fast)
Built from the PDK's own legacy per-corner model files, swapping the NMOS and PMOS 1.8 V models independently (n=p cases reproduce the PDK ss/tt/ff exactly: 177.993 / 226.206 / 279.178 MHz). Result at V_ctrl = 0.9 V, 27 C:

| f (MHz) | P slow | P typ | P fast |
|---|---|---|---|
| N slow | 178.0 | 188.0 | 195.9 |
| N typ | 211.8 | 226.2 | 238.1 |
| N fast | 242.8 | 262.7 | 279.2 |

tempco (ppm/C): N slow 1070/1118/1151, N typ 648/681/703, N fast 306/325/332. K_VCO/f (1/V): 4.58/4.88/5.12, 3.58/3.92/4.19, 2.70/3.06/3.35. All 8 monotonicity checks pass (f rises with NMOS and with PMOS strength at 0.9 V and at 1.4 V; nsps is the minimum and nfpf the maximum; tempco falls with NMOS strength). PDK sf/fs frequencies are inside the [ss, ff] envelope at 0.9 and 1.4 V; their tempcos (112, 1399 ppm/C) are not inside [332, 1070].

## Physics sanity checks (all pass)
- Vth falls with temperature: NMOS -0.78 mV/C, PMOS |Vth| -1.1 mV/C (tt, -40..85 C); textbook -0.5..-3 mV/C.
- Id at 1.8 V falls with temperature (mobility, -30 % over 125 C, tt NMOS) while Id at 0.9 V rises (+14 %): the bias sits below the zero-temperature-coefficient point, which is why the VCO's frequency rises with T at 0.9 V; at V_ctrl = 1.4 V the tempco is -816 ppm/C (sign flip).
- Tempco, K_VCO/f and (1/overdrive) all rank with NMOS drive (nfps < ... < nspf), as gm/Id theory predicts.
- Operating regime flips which device limits the ring: at 0.9 V the NMOS rows dominate (36 % spread slow->fast N vs 10 % across P), at 1.4 V the PMOS columns dominate (26 % vs 9 %). So no single "textbook" ordering exists for the two skew corners across V_ctrl; at 0.9 V sf > tt, at 1.4 V fs > sf.
- Supply current is ~proportional to frequency (I = N*C*VDD*f, C ~ 27-30 fF per node) in every corner.
- Closed loop: V_ctrl at lock equals the open-loop V_ctrl for 226.2 MHz to within 0.2 mV at all 11 corners (`docs/figures/final_vlock_check.png`).

## Decision
Final-review results are reported on **11 corners**: the 9 textbook corners (ss, tt, ff included) plus the PDK's own sf and fs as wider "foundry skew" extremes, always labelled by device ("PDK sf = fast-N/slow-P").
