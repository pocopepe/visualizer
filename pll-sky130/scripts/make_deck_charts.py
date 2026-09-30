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
           "closed-loop results are tt / 27 °C.", False, RGBColor(0x77, 0x77, 0x77))], size=10)


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
    stat(s, X0, 5000000, 2500000, 1000000, "669 MHz/V", "K_VCO at 0.9 V (tt)")
    stat(s, X0 + 2700000, 5000000, 2500000, 1000000, "≈ 0.63 V", "oscillation floor", RED)
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
        "From a true 0 V start, V_ctrl sits below the 0.63 V oscillation floor: no VCO edges → divider silent → PFD sees only REF → slow pump-up.",
        ("Fix", True, NAVY),
        "Charge pump runs at 5 × I_cp until the divider's first edge, then a one-shot latch drops it to the nominal 20 µA. Result: lock in 839 ns from 0 V (< 2 µs spec)."],
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
    text(s, X0, 5850000, W, 400000, ["Every corner is far outside ±0.3 % uncompensated. N/P-mismatched corners (sf, fs) bracket the range."], size=12)

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

    # J: lock transient
    s = S["lock"] = new_slide(prs, "Closed-Loop Lock Transient", logo)
    ch = xy(s, X0, Y0 - 100000, 7600000, 4700000, [
        ("start 0.85 V (coarse-tuned): 577 ns", [tuple(p) for p in D["lock_coarse"]], TEAL, "line"),
        ("true 0 V cold start (boosted): 839 ns", [tuple(p) for p in D["lock_cold"]], NAVY, "line"),
        hline(0.63, 0, 3000, "VCO floor 0.63 V", RED)],
        xt="Time (ns)", yt="V_ctrl (V)", xmin=0, xmax=3000, ymin=0, ymax=1.2)
    legend(ch, size=10)
    stat(s, 8500000, Y0, 3000000, 1100000, "839 ns", "lock from 0 V cold start")
    stat(s, 8500000, Y0 + 1250000, 3000000, 1100000, "577 ns", "lock from 0.85 V", TEAL)
    stat(s, 8500000, Y0 + 2500000, 3000000, 1100000, "< 2 µs", "spec (analytic model: 450 ns)", GREEN)
    text(s, 8500000, Y0 + 3750000, 3000000, 900000,
         ["Lock = V_ctrl within ±2 % of 0.9 V and staying there."], size=11)
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
            ("669 MHz/V", "K_VCO at 0.9 V, tt", NAVY),
            ("1.12 %", "tt span after 2nd-order (was 8.51 %)", NAVY),
            ("2 / 5", "corners meeting ±0.3 % (ff, sf)", ORANGE),
            ("3.37 MHz", "Monte Carlo mean |drift| after 2nd-order (was 18.93)", TEAL),
            ("23 / 30", "seeds where 2nd-order beats 1st", TEAL),
            ("839 ns", "lock from a true 0 V cold start (< 2 µs)", GREEN),
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
    S = build(prs, logo)
    o = {i + 1: sl for i, sl in enumerate(old)}
    order = [o[1], o[2], o[3], o[4], o[5], S["vco"], S["comp_arch"], S["acq"], S["method"], o[6],
             o[7], S["drift"], S["curv"], o[8], S["comp_tt"], S["comp_corners"],
             o[9], S["lock"], o[10], S["mc"], S["keynums"], o[11], o[12], o[13]]
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
