#!/usr/bin/env python3
"""Extend the 13-slide Review-2 deck with native charts + architecture diagrams.

usage: make_deck_charts.py BASE.pptx OUT.pptx
BASE is the 13-slide deck from commit eddda04 (git show eddda04:Design_of_a_Frequency_Synthesiser_Review-2.pptx).
Chart data comes from results/figdata.json (scripts/make_figdata.py).
"""
import io
from copy import deepcopy
import json
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_AXIS_CROSSES, XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "results/figdata.json").read_text())
FIG, DIA = ROOT / "docs/figures", ROOT / "docs/diagrams"

NAVY, ORANGE, TEAL, GREY, RED, GREEN, PURPLE = (RGBColor.from_string(h) for h in
                                                ("1D2F82", "E07A1F", "2A9D8F", "9AA0A6", "C0392B", "2E8B57", "6A3D9A"))
CC = {"ss": PURPLE, "sf": TEAL, "tt": NAVY, "fs": RED, "ff": ORANGE}
ORDER = ["sf", "ff", "tt", "ss", "fs"]
X0, Y0, W = 640080, 1325880, 10881360  # template body box
DARK = RGBColor(0x33, 0x33, 0x33)


# ---------- slide scaffolding ----------
def new_slide(prs, title, logo_blob):
    s = prs.slides.add_slide(prs.slide_layouts[0])
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    num = next(sh for sh in prs.slides[1].shapes if sh.left == 11460175 and sh.top == 6446520)
    s.shapes._spTree.append(deepcopy(num._element))
    t = s.shapes.add_textbox(548640, 320040, 9601200, 685800)
    t.text_frame.word_wrap = True
    r = t.text_frame.paragraphs[0].add_run()
    r.text = title
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(28), True, "Calibri", NAVY
    s.shapes.add_picture(io.BytesIO(logo_blob), 10362895, 320040, 1371600, 518746)
    return s


def text(s, x, y, w, h, items, size=14):
    """items: list of (text, bold, colour) or plain str; one paragraph each."""
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        txt, bold, col = (it, False, DARK) if isinstance(it, str) else it
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(6)
        r = p.add_run()
        r.text = txt
        r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(size), bold, "Calibri", col
    return tb


def stat(s, x, y, w, h, big, small, col=NAVY, size=26):
    box = s.shapes.add_shape(1, x, y, w, h)
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF2, 0xF4, 0xFB)
    box.line.color.rgb = col
    tf = box.text_frame
    tf.word_wrap = True
    for i, (t, sz, b) in enumerate([(big, size, True), (small, 11, False)]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = t
        r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(sz), b, "Calibri", col if i == 0 else DARK


def picture(s, path, x, y, w, h):
    """Fit image inside (x,y,w,h) preserving aspect, centred."""
    pic = s.shapes.add_picture(str(path), x, y)
    r = min(w / pic.width, h / pic.height)
    pic.width, pic.height = int(pic.width * r), int(pic.height * r)
    pic.left, pic.top = x + (w - pic.width) // 2, y + (h - pic.height) // 2
    return pic


def scope(s):
    text(s, X0, 6130000, 10500000, 280000,
         [("Scope: compensation is an ideal behavioural correction voltage (transistor-level in Review 3); "
           "closed-loop results are tt / 27 °C (corner lock tests: coarse start).", False, RGBColor(0x77, 0x77, 0x77))], size=10)


# ---------- chart helpers ----------
def style_axes(ch, xt, yt, xmin=None, xmax=None, ymin=None, ymax=None):
    for ax, t, lo, hi in ((ch.category_axis, xt, xmin, xmax), (ch.value_axis, yt, ymin, ymax)):
        if t:
            ax.has_title = True
            ax.axis_title.text_frame.text = t
            ax.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(11)
        ax.tick_labels.font.size = Pt(10)
        if lo is not None:
            ax.minimum_scale = lo
        if hi is not None:
            ax.maximum_scale = hi
    # axes meet at the bottom-left, not at x=0 / y=0 in mid-plot
    ch.category_axis.crosses = ch.value_axis.crosses = XL_AXIS_CROSSES.MINIMUM
    ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE3, 0xE3, 0xE3)
    ch.font.name = "Calibri"


def legend(ch, pos=XL_LEGEND_POSITION.BOTTOM, size=10):
    ch.has_legend = True
    ch.legend.position = pos
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(size)


def xy(s, x, y, w, h, series, **ax):
    """series: list of (name, [(x,y)...], colour, style) style in {line, marker, both, dash}"""
    cd = XyChartData()
    for name, pts, _, _ in series:
        se = cd.add_series(name)
        for a, b in pts:
            se.add_data_point(a, b)
    ch = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES, x, y, w, h, cd).chart
    ch.has_title = False
    for ser, (_, _, col, st) in zip(ch.series, series):
        ser.smooth = False
        ln = ser.format.line
        if st == "marker":
            ln.fill.background()
        else:
            ln.color.rgb, ln.width = col, Pt(2.25 if st != "dash" else 1.5)
            if st == "dash":
                ln.dash_style = 4  # MSO_LINE.DASH
        if st in ("marker", "both"):
            ser.marker.style = XL_MARKER_STYLE.CIRCLE if st == "both" else XL_MARKER_STYLE.DIAMOND
            ser.marker.size = 7 if st == "both" else 11
            ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = col
            ser.marker.format.line.color.rgb = col
        else:
            ser.marker.style = XL_MARKER_STYLE.NONE
    style_axes(ch, **ax)
    return ch


def bar(s, x, y, w, h, cats, series, labels_fmt=None, **ax):
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals, _ in series:
        cd.add_series(name, vals)
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, w, h, cd).chart
    ch.has_title = False
    for ser, (_, _, col) in zip(ch.series, series):
        ser.format.fill.solid()
        if isinstance(col, list):  # per-point colours
            for i, c in enumerate(col):
                pt = ser.points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
        else:
            ser.format.fill.fore_color.rgb = col
    if labels_fmt:
        pl = ch.plots[0]
        pl.has_data_labels = True
        pl.data_labels.number_format, pl.data_labels.number_format_is_linked = labels_fmt, False
        pl.data_labels.font.size = Pt(10)
    ch.plots[0].gap_width = 60
    style_axes(ch, **ax)
    return ch


def error_bars(ser, halfwidths):
    """Attach custom +/- Y error bars (c:errBars) to a bar series."""
    eb = etree.SubElement(ser._element, qn("c:errBars"))
    for tag, val in (("errDir", "y"), ("errBarType", "both"), ("errValType", "cust"), ("noEndCap", "0")):
        etree.SubElement(eb, qn(f"c:{tag}")).set("val", val)
    for side in ("plus", "minus"):
        nl = etree.SubElement(etree.SubElement(eb, qn(f"c:{side}")), qn("c:numLit"))
        etree.SubElement(nl, qn("c:ptCount")).set("val", str(len(halfwidths)))
        for i, v in enumerate(halfwidths):
            pt = etree.SubElement(nl, qn("c:pt")); pt.set("idx", str(i))
            etree.SubElement(pt, qn("c:v")).text = f"{v:.4f}"
    sp = etree.SubElement(eb, qn("c:spPr"))
    ln = etree.SubElement(sp, "{http://schemas.openxmlformats.org/drawingml/2006/main}ln"); ln.set("w", "19050")
    sf = etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
    etree.SubElement(sf, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr").set("val", "333333")
    # schema order: errBars must precede c:cat / c:val
    cat = ser._element.find(qn("c:cat"))
    if cat is not None:
        cat.addprevious(eb)


def hide_legend_entry(ch, idx):
    """Drop series idx from the legend (the duplicate -0.3 % spec line)."""
    e = etree.fromstring('<c:legendEntry xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
                         f'<c:idx val="{idx}"/><c:delete val="1"/></c:legendEntry>')
    ch.legend._element.find(qn("c:legendPos")).addnext(e)


def pts(d):
    return sorted((int(k), v) for k, v in d.items())


def hline(y, x0, x1, name, col):
    return (name, [(x0, y), (x1, y)], col, "dash")


# ---------- the new slides ----------
def build(prs, logo):
    S = {}
    tmp = D["temp_dev"]

    # A: VCO schematic + tuning curve
    s = S["vco"] = new_slide(prs, "VCO: Schematic & Tuning Curve", logo)
    picture(s, DIA / "vco_schematic.png", X0, Y0, 5000000, 3500000)
    ch = xy(s, 5800000, Y0 - 100000, 5700000, 3900000,
            [(c, D["tuning"][c], CC[c], "both") for c in ORDER],
            xt="Control voltage V_ctrl (V)", yt="VCO frequency (MHz)", xmin=0.6, xmax=1.4, ymin=0)
    legend(ch)
    stat(s, X0, 5000000, 2500000, 1000000, "887 MHz/V", "local K_VCO at 0.9 V (tt)")
    stat(s, X0 + 2700000, 5000000, 2500000, 1000000, "< 18 MHz", "below 0.65 V (still oscillates)", RED)
    text(s, 5900000, 5050000, 5600000, 1000000, [
        "5-stage current-starved ring: V_ctrl sets the starving current, so it sets the delay per stage.",
        "Design point 0.9 V gives 226 MHz = 8 × 28.275 MHz reference."], size=12)

    # B: compensation architecture
    s = S["comp_arch"] = new_slide(prs, "Temperature-Compensation Architecture", logo)
    picture(s, DIA / "compensation_arch.png", X0, Y0, W, 3300000)
    for i, (big, small, col) in enumerate([
            ("ΔV(T)", "correction added to V_ctrl before the VCO bias generator", NAVY),
            ("1st-order", "linear k1·(T−27): PTAT/CTAT equivalent", TEAL),
            ("2nd-order", "adds k2·(T−27)²: matches the drift's curvature", NAVY),
            ("per corner", "k1, k2 fitted separately at tt/ff/ss/sf/fs", ORANGE)]):
        stat(s, X0 + i * 2760000, 4800000, 2600000, 1150000, big, small, col)
    scope(s)

    # C: acquisition boost
    s = S["acq"] = new_slide(prs, "Cold-Start Fix: Boosted Charge Pump", logo)
    picture(s, DIA / "acq_boost.png", X0, Y0, W, 2900000)
    text(s, X0, 4400000, W, 1700000, [
        ("Problem (open since Review 1)", True, NAVY),
        "From a true 0 V start the VCO is in deep subthreshold (0.6 MHz at 0.5 V, 6.5 MHz at 0.6 V, vs 226 MHz target): the divided clock is effectively absent → PFD sees only REF → slow pump-up at 20 µA.",
        ("Fix", True, NAVY),
        "Charge pump runs at 5 × I_cp until the divider's first edge, then a one-shot latch drops it to the nominal 20 µA. Result: lock in 1352 ns from 0 V with the retuned loop filter (839 ns with the original), inside the 2 µs spec."],
        size=13)

    # D: methodology
    s = S["method"] = new_slide(prs, "Methodology: Review 1 → Review 2 → Review 3", logo)
    picture(s, DIA / "method_flow.png", X0, Y0, W, 4600000)

    # E: uncompensated drift
    s = S["drift"] = new_slide(prs, "Uncompensated Drift: All 5 Corners", logo)
    ch = xy(s, X0, Y0 - 100000, 6600000, 4500000,
            [(f"{c} ({D['tempco_ppm'][c]:.0f} ppm/°C)", pts(tmp[c]), CC[c], "both") for c in ORDER]
            + [hline(0.3, -40, 85, "±0.3 % spec", GREEN), hline(-0.3, -40, 85, " ", GREEN)],
            xt="Temperature (°C)", yt="Δf vs 27 °C (%)", xmin=-40, xmax=85)
    legend(ch, size=9)
    hide_legend_entry(ch, len(ORDER) + 1)
    ch = bar(s, 7400000, Y0 - 100000, 4100000, 3200000, ORDER,
             [("tempco", [D["tempco_ppm"][c] for c in ORDER], [CC[c] for c in ORDER])],
             labels_fmt="0", xt="corner", yt="ppm/°C")
    ch.has_legend = False
    ch.has_title = True; ch.chart_title.text_frame.text = "Average tempco, −40→85 °C"
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    stat(s, 7400000, 4550000, 1950000, 1150000, "12.5×", "tempco spread sf→fs", RED)
    stat(s, 9550000, 4550000, 1950000, 1150000, "8.5 %", "tt span, −40→85 °C")
    text(s, X0, 5850000, W, 400000, ["Every corner is far outside ±0.3 % uncompensated. Tempco ranks with NMOS drive: see next slide."], size=12)

    # E2: why the corners order this way
    s = S["why"] = new_slide(prs, "Why the Corners Order This Way", logo)
    nmos = {"sf": 45.1, "ff": 42.8, "tt": 36.2, "ss": 30.3, "fs": 28.2}  # NMOS Id (uA), |Vgs|=0.9 V, W/L=2/0.5, 27 C
    ch = xy(s, X0, Y0 - 100000, 6200000, 4500000,
            [(f"{c}", [(nmos[c], D["tempco_ppm"][c])], CC[c], "marker") for c in ORDER],
            xt="NMOS drive current at |Vgs| = 0.9 V (µA)", yt="Uncompensated tempco (ppm/°C)", xmin=26, xmax=48, ymin=0, ymax=1600)
    for ser in ch.series:
        ser.marker.size = 14
    legend(ch, size=10)
    text(s, 7000000, Y0, 4500000, 3300000, [
        ("Reading the chart", True, NAVY),
        "V_ctrl drives the NMOS starving gate directly and sets the PMOS bias through a mirror, so NMOS overdrive sets the ring current.",
        "Less overdrive → the threshold-voltage drop with temperature is a bigger share of it and beats the mobility drop → stronger positive tempco.",
        ("Corner labels in this PDK", True, NAVY),
        "sf = fast-NMOS / slow-PMOS, fs = slow-NMOS / fast-PMOS. The skew corners shift NMOS Vth ±27 mV (ss/ff only ±15 mV), so they bracket the range."], size=12)
    stat(s, 7000000, 4750000, 2150000, 1150000, "−816 ppm/°C", "tt tempco at V_ctrl = 1.4 V (sign flips)", TEAL, size=20)
    stat(s, 9350000, 4750000, 2150000, 1150000, "+681 ppm/°C", "tt tempco at V_ctrl = 0.9 V", NAVY, size=20)
    text(s, X0, 5900000, 6200000, 300000, ["Sign flip = a zero-tempco bias point exists between 0.9 and 1.4 V (textbook behaviour)."], size=11)

    # F: curvature
    s = S["curv"] = new_slide(prs, "Why Second Order? The Drift Is Curved", logo)
    lab, v = zip(*D["tt_local_tempco"])
    ch = bar(s, X0, Y0 - 100000, 6400000, 4600000, [l.replace(" to ", "→") for l in lab],
             [("local tempco", list(v), NAVY)], labels_fmt="0",
             xt="temperature interval (°C)", yt="local tempco at tt (ppm/°C)", ymin=0)
    ch.has_legend = False
    text(s, 7300000, Y0, 4200000, 4600000, [
        ("Reading the chart", True, NAVY),
        "If the drift were a straight line, every bar would be the same height (the 681 ppm/°C average).",
        "Instead the slope falls 3.2× from cold (1123) to hot (352) — the drift is curved.",
        ("Consequence", True, NAVY),
        "A linear (1st-order) correction can only match the average slope: it leaves a bowed residual.",
        "A quadratic term k2·(T−27)² matches the curvature → 2nd-order compensation."], size=13)

    # G: compensation at tt
    s = S["comp_tt"] = new_slide(prs, "Compensation at the Typical (tt) Corner", logo)
    c = D["comp"]["tt"]
    ch = xy(s, X0, Y0 - 100000, 7300000, 4700000, [
        ("uncompensated", pts(c["base_dev"]), GREY, "both"),
        ("1st-order", pts(c["first_dev"]), TEAL, "both"),
        ("2nd-order (refit)", pts(c["second_dev"]), NAVY, "both"),
        ("2nd-order, naive coeffs", pts(D["tt_naive_dev"]), RED, "dash"),
        ("held-out temps (never fitted)", pts(c["holdout_dev"]), ORANGE, "marker"),
        hline(0.3, -40, 85, "±0.3 % spec", GREEN), hline(-0.3, -40, 85, " ", GREEN)],
        xt="Temperature (°C)", yt="Δf vs 27 °C (%)", xmin=-40, xmax=85)
    legend(ch, size=9)
    hide_legend_entry(ch, 6)
    stat(s, 8200000, Y0, 3300000, 1000000, "8.51 → 1.12 %", "span: baseline → 2nd-order")
    stat(s, 8200000, Y0 + 1150000, 3300000, 1000000, "7.57×", "compensation ratio C at tt", TEAL)
    stat(s, 8200000, Y0 + 2300000, 3300000, 1000000, "±0.87 %", "max |dev|: spec ±0.3 % NOT met", RED)
    text(s, 8200000, Y0 + 3450000, 3300000, 1300000, [
        "Naive analytical k2 over-corrects the cold end (+4.1 % at −40 °C); refitting on the 1st-order residual fixes it.",
        "Orange diamonds: temperatures never used in fitting, all inside the envelope."], size=11)
    scope(s)

    # H: per-corner residuals (log bars + spec line need matplotlib)
    s = S["comp_corners"] = new_slide(prs, "Residual Drift per Corner vs ±0.3 % Spec", logo)
    picture(s, FIG / "comp_corners.png", X0, Y0 - 100000, 7000000, 4700000)
    for i, (cn, ok) in enumerate([("ff", True), ("sf", True), ("tt", False), ("ss", False), ("fs", False)]):
        v = D["comp"][cn]["maxdev_2nd"]
        stat(s, 7900000, Y0 + i * 900000, 3600000, 800000, f"{cn}: {v:.2f} %",
             "meets spec" if ok else "misses spec", GREEN if ok else RED)
    scope(s)

    # J: lock transient (retuned loop filter, R2 = 3.6k)
    s = S["lock"] = new_slide(prs, "Closed-Loop Lock Transient (Retuned Loop)", logo)
    ch = xy(s, X0, Y0 - 100000, 7600000, 4700000, [
        ("start 0.85 V (coarse-tuned): 503 ns", [tuple(p) for p in D["lock_coarse_new"]], TEAL, "line"),
        ("true 0 V cold start (boosted): 1352 ns", [tuple(p) for p in D["lock_cold_new"]], NAVY, "line"),
        hline(0.65, 0, 3000, "below 0.65 V the VCO is < 18 MHz", RED)],
        xt="Time (ns)", yt="V_ctrl (V)", xmin=0, xmax=3000, ymin=0, ymax=1.2)
    legend(ch, size=10)
    stat(s, 8500000, Y0, 3000000, 1050000, "1352 ns", "lock from 0 V cold start (was 839 ns)", NAVY)
    stat(s, 8500000, Y0 + 1150000, 3000000, 1050000, "503 ns", "lock from 0.85 V (was 577 ns)", TEAL)
    stat(s, 8500000, Y0 + 2300000, 3000000, 1050000, "< 2 µs", "spec: met at both starts", GREEN)
    text(s, 8500000, Y0 + 3450000, 3000000, 1200000, [
        "Lock = V_ctrl within ±2 % of 0.9 V and staying there.",
        "R2 = 3.6 kΩ. The retune makes the cold start slower (+61 %) but well damped."], size=11)
    scope(s)

    # J2: loop dynamics: found, fixed, verified
    s = S["loopdyn"] = new_slide(prs, "Loop Dynamics: Found, Fixed, Verified", logo)
    ch = xy(s, X0, Y0 - 100000, 6000000, 4300000, [
        ("original R2 = 1.7 kΩ (ζ ≈ 0.33): 577 ns", [tuple(p) for p in D["lock_coarse"] if p[0] <= 2000], ORANGE, "line"),
        ("retuned R2 = 3.6 kΩ (ζ ≈ 0.70): 503 ns", [tuple(p) for p in D["lock_coarse_new"] if p[0] <= 2000], NAVY, "line")],
        xt="Time (ns)", yt="V_ctrl (V)", xmin=0, xmax=2000, ymin=0.82, ymax=0.96)
    legend(ch, size=10)
    stat(s, 6900000, Y0, 2150000, 1050000, "ζ 0.33 → 0.70", "damping (Review 1 claimed 0.72)", NAVY, size=20)
    stat(s, 9250000, Y0, 2250000, 1050000, "≈ 30° → 65°+", "phase margin (100·ζ rule)", NAVY, size=20)
    stat(s, 6900000, Y0 + 1200000, 2150000, 1050000, "8.6 → 0.35 mV", "V_ctrl ripple at lock", GREEN, size=20)
    stat(s, 9250000, Y0 + 1200000, 2250000, 1050000, "0.78 → 0.008 %", "residual frequency error at 2 µs", GREEN, size=20)
    text(s, 6900000, Y0 + 2450000, 4600000, 2200000, [
        ("Found", True, NAVY),
        "Review 1 dropped the 1/(2π) of the charge-pump gain, so ζ was really 0.33, not 0.72.",
        ("Fixed", True, NAVY),
        "R2 1.7 → 3.6 kΩ (C1, C2, I_cp unchanged), verified at transistor level.",
        ("Cost", True, NAVY),
        "0 V cold start 839 → 1352 ns; both inside the 2 µs spec."], size=11)
    text(s, X0, 5500000, 6000000, 500000, ["Measured local K_VCO = 887 MHz/V (Review 1 used 669)."], size=11)
    scope(s)

    # J3: lock across all five corners
    s = S["lockcorn"] = new_slide(prs, "Lock Across All Five Corners", logo)
    lcn = D["lock_corners"]
    corners = ["ff", "sf", "tt", "fs", "ss"]
    new_ns = [lcn[c]["3.6k"].get("lock_ns_5us", lcn[c]["3.6k"]["lock_ns"]) for c in corners]
    ch = bar(s, X0, Y0 - 100000, 5600000, 4400000, corners,
             [("lock time (ns)", new_ns, [CC[c] for c in corners])], labels_fmt="0",
             xt="process corner (retuned loop, R2 = 3.6 kΩ)", yt="lock time from 0.85 V start (ns)", ymin=0, ymax=2200)
    ch.has_legend = False
    text(s, 6500000, Y0 - 100000, 5000000, 1500000, [
        ("Retuned loop: all five corners lock inside the 2 µs spec", True, NAVY),
        "Settled V_ctrl differs by corner (ss needs 0.968 V, the weakest NMOS); final f_VCO within 0.1 % of 226.2 MHz at ff, sf, tt, fs."], size=12)
    rows = [("corner", "retuned lock", "final f_VCO", "original loop")]
    for c in corners:
        n, o = lcn[c]["3.6k"], lcn[c]["1.7k"]
        f_new = f"{n['f_vco_MHz']:.1f} MHz" if c != "ss" else "settled (5 µs run)"
        orig = (f"{o['lock_ns']:.0f} ns" if c == "tt" else
                "1737 ns (5 µs run)" if c == "ss" else f"not settled at 2 µs ({o['f_vco_MHz']:.1f} MHz)")
        rows.append((c, f"{new_ns[corners.index(c)]:.0f} ns", f_new, orig))
    gt = s.shapes.add_table(len(rows), 4, 6500000, Y0 + 1450000, 5000000, 2600000).table
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = gt.cell(i, j)
            cell.text = v
            r = cell.text_frame.paragraphs[0].runs[0]
            r.font.size, r.font.name, r.font.bold = Pt(10), "Calibri", i == 0
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if i == 0 else (RGBColor(0xF2, 0xF4, 0xFB) if i % 2 else RGBColor(0xFF, 0xFF, 0xFF))
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i == 0 else DARK
    text(s, 6500000, Y0 + 4150000, 5000000, 800000, [
        "The original loop had not finished settling at ff/sf/fs/ss within the 2 µs run, so no lock time is quoted for it there. Corner runs use the coarse start; the 0 V cold start was run at tt only."], size=10)
    scope(s)

    # I: Monte Carlo charts
    s = S["mc"] = new_slide(prs, "Monte Carlo: Paired Comparison (tt)", logo)
    m = D["mc_absdrift"]
    seeds = sorted(set(m["first"]) & set(m["second"]), key=int)
    lim = 16
    ch = xy(s, X0, Y0 - 100000, 5000000, 4700000, [
        ("one mismatch sample (seed)", [(m["first"][k], m["second"][k]) for k in seeds], NAVY, "marker"),
        ("equal drift (y = x)", [(0, 0), (lim, lim)], GREY, "dash")],
        xt="1st-order |drift| (MHz)", yt="2nd-order |drift| (MHz)", xmin=0, xmax=lim, ymin=0, ymax=lim)
    ch.series[0].marker.size = 8
    legend(ch, size=10)
    arms = [("baseline", "uncompensated"), ("first", "1st-order"), ("second", "2nd-order")]
    from stats import ci95
    mus, hws = zip(*(ci95(list(m[k].values())) for k, _ in arms))
    ch = bar(s, 5900000, Y0 - 100000, 5600000, 3500000,
             [f"{a[1]}\n{mu:.2f} MHz (n={len(m[a[0]])})" for a, mu in zip(arms, mus)],
             [("mean |drift|", list(mus), [GREY, TEAL, NAVY])],
             xt="", yt="mean |drift| 85 vs −40 °C (MHz)", ymin=0, ymax=25)
    ch.has_legend = False
    error_bars(ch.series[0], hws)
    stat(s, 5900000, 4750000, 1750000, 1100000, "23 / 30", "seeds where 2nd < 1st", size=20)
    stat(s, 7825000, 4750000, 1750000, 1100000, "−2.48 MHz", "95 % CI [0.81, 4.15]", TEAL, size=20)
    stat(s, 9750000, 4750000, 1750000, 1100000, "p < 0.05", "paired t + Wilcoxon", GREEN, size=20)
    text(s, X0, 5900000, 5000000, 300000, ["Points below the dashed line: 2nd-order beat 1st-order on that same chip."], size=11)

    # K: key numbers
    s = S["keynums"] = new_slide(prs, "Review 2 at a Glance", logo)
    nums = [("12.5×", "tempco spread across 5 corners (112→1399 ppm/°C)", RED),
            ("887 MHz/V", "local K_VCO at 0.9 V, tt", NAVY),
            ("1.12 %", "tt span after 2nd-order (was 8.51 %)", NAVY),
            ("2 / 5", "corners meeting ±0.3 % (ff, sf)", ORANGE),
            ("3.37 MHz", "Monte Carlo mean |drift| after 2nd-order (was 18.93)", TEAL),
            ("23 / 30", "seeds where 2nd-order beats 1st", TEAL),
            ("1352 ns", "lock from a true 0 V cold start, retuned loop (< 2 µs)", GREEN),
            ("15", "IEEE references; 1 patent narrowed our novelty claim", GREY)]
    for i, (a, b, col) in enumerate(nums):
        stat(s, X0 + (i % 4) * 2760000, Y0 + (i // 4) * 2000000, 2600000, 1800000, a, b, col)
    scope(s)
    return S


def main(base, out):
    prs = Presentation(base)
    logo = next(sh for sh in prs.slides[1].shapes if sh.shape_type == 13).image.blob
    old = list(prs.slides)
    # fix numbers in existing tables (see FINDINGS_PERCORNER.md, analyze_mc.py output)
    for sl in old:
        for sh in sl.shapes:
            if sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        for p in cell.text_frame.paragraphs:
                            for r in p.runs:
                                if row.cells[0].text == "sf" and r.text == "1.40%":
                                    r.text = "1.48%"
                                r.text = r.text.replace("5.86 MHz", "5.85 MHz")
    # slide 5: swap in the current block diagram (the base deck embeds an older render)
    arch = old[4]
    pic = next(sh for sh in arch.shapes if sh.shape_type == 13 and sh.width == W)
    picture(arch, DIA / "pll_block_diagram.png", pic.left, pic.top, pic.width, 3196694)
    pic._element.getparent().remove(pic._element)
    sub = {  # exact paragraph text on the original slides -> corrected text
        "VCO tuning: K_VCO ~= 669 MHz/V at 0.9V (polynomial fit, not a secant); 18->358 MHz over 0.65->1.40V. Oscillation lost below ~0.60-0.65V (device-threshold-limited).":
            "VCO tuning: local K_VCO ~= 890 MHz/V at 0.9 V (tt, central difference +/-50 mV; an earlier whole-curve quadratic fit gave 669, too low); 18->358 MHz over 0.65->1.40 V. No hard floor: below 0.65 V the ring still oscillates, slowly (6.5 MHz at 0.6 V, 0.6 MHz at 0.5 V).",
        "Sensitivity insight: N/P-mismatched corners (sf, fs) bracket the entire tempco range, not the matched-speed corners (ff, ss) -- points at current-source balance, not absolute device speed, as the driving mechanism.":
            "Tempco ranks with NMOS drive at 0.9 V (sf 45 uA ... fs 28 uA): less overdrive => the threshold drop with temperature dominates => stronger positive tempco. Sign flips at V_ctrl = 1.4 V (-816 ppm/C). sf/fs bracket the range because sky130 skew corners shift NMOS Vth +/-27 mV (ss/ff +/-15 mV).",
        "669": "887",
        "(tt, 0.9V, fit-derivative)": "(tt, 0.9 V, local slope)",
        "< 2us spec; ~450ns analytical": "< 2us spec",
        "577 ns": "503 ns (was 577 ns)", "839 ns": "1352 ns (was 839 ns)",
        "0.902 V": "0.9000 V (was 0.902)", "0.9002 V": "0.9000 V",
        "227.96 MHz": "226.18 MHz (was 227.96)", "226.42 MHz": "225.98 MHz (was 226.42)",
        "839 ns (0V cold start)": "1352 ns (0V cold start)",
        "Coarse-tuned start (0.85V)": "Coarse-tuned start (0.85V), R2 = 3.6k",
        "TRUE cold start (0V, boosted)": "TRUE cold start (0V, boosted), R2 = 3.6k",
        "580.2": "582", "763.6": "936", "669.3": "887", "568.2": "815", "688.7": "1018",
    }
    for sl in old:
        for sh in sl.shapes:
            paras = [p for r in sh.table.rows for c in r.cells for p in c.text_frame.paragraphs] if sh.has_table \
                else (sh.text_frame.paragraphs if sh.has_text_frame else [])
            for p in paras:
                t = p.text.strip()
                new = sub.get(t)
                if new is None and "they assume constant K_VCO, which is false." in t:
                    new = t.replace("they assume constant K_VCO, which is false.", "they assume constant K_VCO (false) and used a K_VCO ~25% too low (669 vs 887 MHz/V).")
                if new is None and "Transistor-level charge pump; layout in Magic" in t:
                    new = ("Re-verify the retuned loop (zeta ~0.7, R2 = 3.6 kOhm) with a transistor-level charge pump; "
                           "layout in Magic, DRC, LVS (netgen), post-layout re-simulation.")
                for old_s, new_s in (("now locks in 839 ns.", "now locks in 1352 ns (retuned loop filter)."),
                                     ("locks in 839 ns, comfortably inside the 2us spec -- worked on the first simulation attempt.",
                                      "locks in 1352 ns with the retuned loop filter (839 ns with the original R2 = 1.7 kOhm), inside the 2us spec.")):
                    if new is None and old_s in t:
                        new = t.replace(old_s, new_s)
                if new is not None and p.runs:
                    p.runs[0].text = new
                    for r in p.runs[1:]:
                        r.text = ""
    for sh in old[6].shapes:  # slide 7 stat box: replace by run (paragraph text is split)
        if sh.has_text_frame:
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    r.text = r.text.replace("fit-derivative", "local slope").replace("0.9V", "0.9 V")
    for sh in old[6].shapes:  # slide 7 table: sf/fs NMOS/PMOS labels were backwards
        if sh.has_table:
            for row in sh.table.rows:
                if row.cells[0].text in ("sf", "fs"):
                    row.cells[1].text_frame.paragraphs[0].runs[0].text = "fast / slow" if row.cells[0].text == "sf" else "slow / fast"
    S = build(prs, logo)
    o = {i + 1: sl for i, sl in enumerate(old)}
    order = [o[1], o[2], o[3], o[4], o[5], S["vco"], S["comp_arch"], S["acq"], S["method"], o[6],
             o[7], S["drift"], S["why"], S["curv"], o[8], S["comp_tt"], S["comp_corners"],
             o[9], S["lock"], S["loopdyn"], S["lockcorn"], o[10], S["mc"], S["keynums"], o[11], o[12], o[13]]
    lst = prs.slides._sldIdLst
    by_id = {el.get("id"): el for el in lst}
    els = [by_id[str(sl.slide_id)] for sl in order]
    for el in els:
        lst.append(el)  # re-appending moves it to the end, in order
    for n, sl in enumerate(prs.slides, 1):  # page numbers: textbox at the template's number position
        for sh in sl.shapes:
            if sh.has_text_frame and sh.left == 11460175 and sh.top == 6446520:
                sh.text_frame.paragraphs[0].runs[0].text = str(n)
    prs.save(out)
    print("wrote", out, len(prs.slides), "slides")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main(*sys.argv[1:3])
