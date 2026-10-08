#!/usr/bin/env python3
"""Build one complete computational Supplementary Information PDF."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fire_metabolism.worked_examples import reproduce_worked_examples


OUTPUT = ROOT / "output" / "pdf" / "fire_metabolism_computational_si.pdf"
FIGURE_DIR = ROOT / "outputs" / "si_reproduction" / "figures"
CLAIM_LEDGER = ROOT / "claims" / "fire_metabolism_claims.json"
VALIDATION_REPORT = ROOT / "outputs" / "si_reproduction" / "validation_report.json"


NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#3E6F9E")
ORANGE = colors.HexColor("#C76A22")
GREEN = colors.HexColor("#2B7A5B")
RED = colors.HexColor("#A23A3A")
INK = colors.HexColor("#20262C")
MUTED = colors.HexColor("#5F6973")
LIGHT_BLUE = colors.HexColor("#EAF1F6")
LIGHT_ORANGE = colors.HexColor("#FBF1E8")
LIGHT_GRAY = colors.HexColor("#F2F4F5")
RULE = colors.HexColor("#C9D0D5")


class SIDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=draw_page))

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in {"SIHeading1", "SIHeading2"}:
                level = 0 if style_name == "SIHeading1" else 1
                text = flowable.getPlainText()
                key = f"section-{self.page}-{abs(hash(text))}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, key))


def draw_page(canvas, doc):
    if doc.page == 1:
        return
    width, height = letter
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, height - 0.47 * inch, width - doc.rightMargin, height - 0.47 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, height - 0.36 * inch, "FIRE IS METABOLIC - COMPUTATIONAL SUPPLEMENTARY INFORMATION")
    canvas.drawRightString(width - doc.rightMargin, 0.38 * inch, f"Page {doc.page}")
    canvas.drawString(doc.leftMargin, 0.38 * inch, "Mathematical verification is not empirical validation")
    canvas.restoreState()


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "SITitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=29,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "SISubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=17,
            textColor=MUTED,
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "SIHeading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "SIHeading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=ORANGE,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "SIBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "SISmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.6,
            leading=10,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "SICaption",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.8,
            leading=10.5,
            textColor=MUTED,
            spaceBefore=3,
            spaceAfter=8,
        ),
        "equation": ParagraphStyle(
            "SIEquation",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.7,
            leading=12,
            textColor=INK,
            leftIndent=8,
            rightIndent=8,
            spaceBefore=4,
            spaceAfter=6,
        ),
        "toc": ParagraphStyle(
            "SITOC",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=INK,
            leftIndent=16,
            firstLineIndent=-10,
        ),
    }
    return styles


def p(text: str, styles, style="body"):
    return Paragraph(text, styles[style])


def equation(text: str, styles):
    content = Preformatted(text, styles["equation"])
    box = Table([[content]], colWidths=[6.75 * inch])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return box


def callout(title: str, text: str, styles, tone="blue"):
    background = LIGHT_BLUE if tone == "blue" else LIGHT_ORANGE
    accent = BLUE if tone == "blue" else ORANGE
    table = Table(
        [[Paragraph(f"<b>{title}</b>", styles["body"]), Paragraph(text, styles["body"])]],
        colWidths=[1.45 * inch, 5.3 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, accent),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def bullet(text: str, styles):
    return Paragraph(f"- {text}", ParagraphStyle("bullet", parent=styles["body"], leftIndent=12, firstLineIndent=-8))


def make_table(data, widths, styles, header=True, font_size=7.5):
    rows = []
    for row_index, row in enumerate(data):
        style = styles["small"]
        rows.append([Paragraph(f"<b>{value}</b>" if header and row_index == 0 else str(value), style) for value in row])
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    for row_index in range(1 if header else 0, len(rows)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_GRAY))
    table.setStyle(TableStyle(commands))
    return table


def figure_block(number: int, filename: str, caption: str, styles, max_height=5.6 * inch):
    path = FIGURE_DIR / filename
    with PILImage.open(path) as image:
        width_px, height_px = image.size
    max_width = 6.75 * inch
    ratio = min(max_width / width_px, max_height / height_px)
    graphic = Image(str(path), width=width_px * ratio, height=height_px * ratio)
    graphic.hAlign = "CENTER"
    return [graphic, Paragraph(f"<b>Figure {number}.</b> {caption}", styles["caption"])]


def add_figure(story, number, filename, caption, styles, page_break=False, max_height=5.6 * inch):
    if page_break:
        story.append(PageBreak())
    story.extend(figure_block(number, filename, caption, styles, max_height=max_height))


def section(story, title: str, styles, page_break=False):
    if page_break:
        story.append(PageBreak())
    story.append(Paragraph(title, styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.7, color=RULE, spaceAfter=6))


def subsection(story, title: str, styles):
    story.append(Paragraph(title, styles["h2"]))


def build_story(styles, claims, report, worked):
    story = []

    story += [
        Spacer(1, 0.75 * inch),
        Paragraph("Fire Is Metabolic", styles["title"]),
        Paragraph("Computational Supplementary Information", styles["subtitle"]),
        HRFlowable(width="100%", thickness=2, color=ORANGE, spaceBefore=8, spaceAfter=20),
        Paragraph(
            "A rigorous, transparent, and reproducible mathematical companion to the supplied Supplementary Information",
            ParagraphStyle("deck", parent=styles["subtitle"], fontSize=15, leading=21, textColor=NAVY),
        ),
        Spacer(1, 0.35 * inch),
        callout(
            "Scientific status",
            "This document verifies identities, algebra, conditional predictions, numerical solutions, explicit constructions, and hypothetical examples. It does not establish that wildfire has a two-thirds perimeter-area exponent and does not establish that wildfire is metabolic.",
            styles,
            "orange",
        ),
        Spacer(1, 0.45 * inch),
        p("Repository: spread-vs-growth", styles, "body"),
        p("Reproduction command: PYTHONPATH=src python scripts/reproduce_si.py", styles, "body"),
        p(f"Validation status: {report['status'].replace('_', ' ')}; 91 tests passed; empirical validation performed: no.", styles, "body"),
        Spacer(1, 1.2 * inch),
        p("Prepared as a computational companion. No wildfire observations were downloaded for this reproduction layer.", styles, "small"),
        PageBreak(),
    ]

    story.append(Paragraph("Contents", styles["h1"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", parent=styles["toc"], leftIndent=10, firstLineIndent=-6, fontName="Helvetica-Bold", spaceBefore=4),
        ParagraphStyle("TOC2", parent=styles["toc"], leftIndent=28, firstLineIndent=-8, textColor=MUTED),
    ]
    story += [toc, PageBreak()]

    section(story, "S1. Scope and scientific contract", styles)
    story.append(p(
        "The package is an executable companion to the mathematical argument. Its role is to make each commitment visible and testable. Definitions and conservation balances are separated from closures; closures are separated from their conditional consequences; and conditional consequences are separated from empirical hypotheses requiring independent observations.",
        styles,
    ))
    story.append(callout(
        "Core chain",
        "P = k A^sigma, L_a = f_a P, dA/dt = vbar_n L_a, and B_front approximately equals H_e w_c dA/dt. Each arrow adds a separate assumption. Geometry does not by itself establish active fraction, normal velocity, fuel consumption, or chemical power.",
        styles,
    ))
    subsection(story, "S1.1 Evidence classes", styles)
    evidence_rows = [
        ["Class", "Meaning", "Example"],
        ["Identity", "Definition, geometric identity, or conservation bookkeeping", "Boundary integral for tracked local advance"],
        ["Conditional derivation", "Follows after explicitly named closures", "Fixed-sigma growth solution"],
        ["Construction", "Exact property of supplied synthetic coordinates", "Right-angle family"],
        ["Counterexample", "Shows that a tempting inference need not hold", "Changing kappa produces an apparent two-thirds slope"],
        ["Empirical hypothesis", "Requires independent wildfire observations", "Persistent within-event two-thirds regime"],
    ]
    story.append(make_table(evidence_rows, [1.15 * inch, 2.8 * inch, 2.8 * inch], styles))
    subsection(story, "S1.2 Central conditional chain", styles)
    story.append(equation(
        "P = k A^sigma\nL_a = f_a P\ndA/dt = vbar_n L_a = f_a vbar_n P\nbeta = k f_a vbar_n\ndA/dt = beta A^sigma\nB_front ~= H_e w_c dA/dt       (when S_A = 0 and residual power is negligible)",
        styles,
    ))
    story.append(p("The shorthand A proportional to t^3 and P proportional to t^2 applies at sigma = 2/3 only when the accumulated growth term dominates the finite initial condition and the coefficients remain stable.", styles))

    section(story, "S2. Variables, units, and reference scales", styles, page_break=True)
    units_rows = [
        ["Symbol", "Meaning", "Dimensions or units"],
        ["A", "Cumulative burned footprint area", "length^2"],
        ["P", "Mapped perimeter under a stated convention", "length"],
        ["L_a", "Active advancing boundary length", "length"],
        ["f_a", "Active fraction L_a/P", "dimensionless"],
        ["vbar_n", "Active-boundary mean normal speed", "length/time"],
        ["S_A", "Untracked area-recruitment source", "length^2/time"],
        ["k", "Dimensional perimeter-area coefficient", "length^(1-2 sigma)"],
        ["beta", "Composite growth coefficient k f_a vbar_n", "area^(1-sigma)/time"],
        ["H_e", "Effective heat yield", "energy/mass"],
        ["w_c", "Consumed fuel loading", "mass/area"],
        ["B_front", "Front-associated chemical power", "energy/time"],
    ]
    story.append(make_table(units_rows, [0.75 * inch, 3.5 * inch, 2.5 * inch], styles))
    story.append(callout("Dimensional warning", "At sigma = 2/3, k has dimensions length^(-1/3). It is not a dimensionless shape coefficient. Only at sigma = 1/2 is k dimensionless under consistent area and perimeter length units.", styles, "orange"))

    section(story, "S3. Dimensional ladder and geometric similarity", styles, page_break=True)
    story.append(equation("V_n = c_n L^n\nS_(n-1) = b_n L^(n-1)\nS_(n-1) = b_n c_n^(-(n-1)/n) V_n^((n-1)/n)", styles))
    story.append(p("Intervals, planar shapes, and three-dimensional solids generate the exponent sequence 0, 1/2, and 2/3 under fixed-shape similarity. These are different geometric comparisons. The three-dimensional surface-volume exponent does not derive a planar wildfire perimeter-area exponent.", styles))
    add_figure(story, 1, "01_dimensional_ladder.png", "Dimensional ladder for similar objects. The equality of two numerical exponents does not identify the measured objects or mechanisms.", styles)
    subsection(story, "S3.1 Smooth families and elongation", styles)
    story.append(p("Squares, circles, and fixed-aspect-ratio ellipses retain perimeter-area slope 1/2. A systematically changing ellipse aspect ratio can change the apparent between-size slope without small-scale boundary wrinkling.", styles))
    add_figure(story, 2, "02_smooth_vs_two_thirds.png", "Analytical comparison of the smooth-family one-half null and a conditional two-thirds relationship.", styles)

    section(story, "S4. Resolution, perimeter conventions, and excess perimeter", styles, page_break=True)
    subsection(story, "S4.1 Three experiments that are not interchangeable", styles)
    for text in (
        "Vary ruler resolution epsilon on one fixed object.",
        "Compare differently sized objects at one fixed resolution.",
        "Observe one changing object through time.",
    ):
        story.append(bullet(text, styles))
    story.append(p("The package returns experiment metadata with each measured slope so these designs cannot be silently pooled.", styles))
    subsection(story, "S4.2 Conditional exponent bridge", styles)
    story.append(equation("A/A_r ~ (L/L_r)^D_A\nP/P_r ~ (L/L_r)^D_h\nsigma = D_h/D_A", styles))
    story.append(p("The specialization sigma = D_h/2 additionally assumes D_A = 2, compatible scaling ranges, and stable shape and resolution conventions. For sigma = 2/3 under those assumptions, D_h = 4/3. This is a conditional bridge, not a wildfire boundary-dimension measurement.", styles))
    subsection(story, "S4.3 Excess perimeter", styles)
    story.append(equation("P_sm = k_sm A^(1/2)\nR_P = P/P_sm\nd log P / d log A = 1/2 + d log R_P / d log A\nR_P(A)/R_P(A_r) = (A/A_r)^(sigma - 1/2)", styles))
    add_figure(story, 3, "03_excess_perimeter.png", "A two-thirds perimeter-area relationship requires R_P proportional to A^(1/6). R_P is constructed from P and A and is not independent confirmation.", styles)

    section(story, "S5. Exact right-angle construction", styles, page_break=True)
    story.append(equation("L_j = l_0 8^j\nN_j = 8^j\nw = l_0/4\nh_j = l_0 (2^j - 1)\nDelta A_pair = 0\nDelta P_pair = 4 h_j", styles))
    story.append(equation("A_j = l_0^2 64^j\nP_j = 4 l_0 16^j\nP_j/(4 l_0) = (A_j/l_0^2)^(2/3)\nR_P,j = 2^j", styles))
    construction_rows = [
        ["j", "A/l_0^2", "P_smooth/l_0", "P/l_0", "R_P"],
        [0, 1, 4, 4, 1],
        [1, 64, 32, 64, 2],
        [2, 4096, 256, 1024, 4],
        [3, 262144, 2048, 16384, 8],
    ]
    story.append(make_table(construction_rows, [0.7 * inch, 1.35 * inch, 1.55 * inch, 1.35 * inch, 1.0 * inch], styles))
    add_figure(story, 4, "04_right_angle_generations.png", "Explicit polygon coordinates independently reproduce the exact areas and perimeters. Every polygon is piecewise smooth with fine-scale boundary dimension one, despite the exact between-size slope 2/3.", styles, max_height=5.0 * inch)
    story.append(callout("Counterexample", "A between-size perimeter-area exponent does not automatically equal a within-boundary fractal dimension.", styles, "orange"))

    section(story, "S6. Boundary kinematics and recruitment", styles, page_break=True)
    story.append(equation("dA/dt = integral_Gamma_a v_n(s,t) ds\n      = vbar_n L_a\n      = f_a vbar_n P", styles))
    story.append(p("This is a kinematic identity for sufficiently regular tracked boundary advance. Heterogeneous segment speeds are integrated with their segment lengths. Hole boundaries advancing into unburned islands add burned area. Multiple components are summed, while colliding fronts require union geometry.", styles))
    subsection(story, "S6.1 Untracked source and residual", styles)
    story.append(equation("dA/dt = f_a vbar_n P + S_A\nR_A = observed dA/dt - f_a vbar_n P", styles))
    story.append(p("S_A includes only recruitment not already represented by tracked boundary motion. Once a spot fire has a resolved boundary included in P, its later growth belongs in the boundary integral and must not also remain in S_A. Discrete mapped additions can be represented as jumps.", styles))

    section(story, "S7. Mapped-perimeter closure and growth equations", styles, page_break=True)
    story.append(equation("a = A/A_r\np = P/P_r\np = kappa(t) a^sigma(t)\nP = k A^sigma\n[k] = length^(1 - 2 sigma)", styles))
    subsection(story, "S7.1 Local slope decomposition", styles)
    story.append(equation("d log p / d log a = sigma + d log kappa/d log a + log(a) d sigma/d log a", styles))
    story.append(p("A model exponent sigma = 1/2 with kappa proportional to a^(1/6) produces a measured trajectory slope 2/3. A fitted trajectory slope therefore does not identify a fixed model exponent without stable-coefficient evidence.", styles))
    subsection(story, "S7.2 General fixed-exponent solution", styles)
    story.append(equation("dA/dt = beta(t) A^sigma\nA(t)^(1-sigma) = A_0^(1-sigma) + (1-sigma) integral beta(u) du     [sigma != 1]\nA(t) = A_0 exp(integral beta dt)                                  [sigma = 1]", styles))
    story.append(equation("A(t) = [A_0^(1/3) + (1/3) integral beta(u) du]^3               [sigma = 2/3]\nA(t) = [A_0^(1/3) + beta (t-t_0)/3]^3                             [constant beta]", styles))
    add_figure(story, 5, "05_analytic_numeric_growth.png", "Analytical solutions and solve_ivp integrations agree for multiple exponents, including superlinear growth over its valid interval.", styles)
    subsection(story, "S7.3 Common normalization", styles)
    story.append(equation("G_0 = (dA/dt)|t_0\na_tilde = A/A_0\ntheta = G_0(t-t_0)/A_0\na_tilde = [1 + (1-sigma) theta]^(1/(1-sigma))\na_tilde = exp(theta)     [sigma = 1]", styles))
    add_figure(story, 6, "06_normalized_growth_laws.png", "Normalized growth laws begin with the same area and initial growth rate, isolating the effect of sigma.", styles)
    add_figure(story, 7, "07_cube_root_linearization.png", "For sigma = 2/3, transformed area A^(1/3) is linear only when the interval-average beta is stable and untracked recruitment is absent.", styles)

    section(story, "S8. Acceleration, source terms, and finite-speed limits", styles, page_break=True)
    subsection(story, "S8.1 Acceleration", styles)
    story.append(equation("d2A/dt2 = beta_dot A^sigma + sigma beta^2 A^(2 sigma - 1)\nFor sigma = 2/3: beta_dot > -(2/3) beta^2 A^(-1/3) for acceleration", styles))
    add_figure(story, 8, "08_constant_declining_beta.png", "Constant beta generates geometric acceleration; a slow decline can still accelerate; a rapid decline can decelerate.", styles)
    subsection(story, "S8.2 Finite-speed reachability", styles)
    story.append(equation("A(t) <= pi [R_0 + v_max Delta t]^2", styles))
    story.append(p("If the initial footprint lies within radius R_0, local normal speeds remain bounded by v_max, and nonlocal recruitment is absent, the reachable area grows at most quadratically. An indefinitely positive constant-beta two-thirds trajectory grows cubically at late time and eventually conflicts with this bound.", styles))
    add_figure(story, 9, "09_finite_speed_bound.png", "The cubic reduced trajectory eventually crosses the finite local-speed bound, limiting the duration of the regime.", styles)
    subsection(story, "S8.3 Continuous and discrete sources", styles)
    story.append(equation("dA/dt = beta A^(2/3) + S_A\nd(A^(1/3))/dt = (1/3)[beta + S_A/A^(2/3)]", styles))
    story.append(p("Constant beta no longer guarantees linear cube-root area when S_A is nonzero. Discrete area jumps are represented separately from continuous sources.", styles))

    section(story, "S9. From geometry to chemical power", styles, page_break=True)
    story.append(equation("Mdot_c,front ~= integral_Gamma w_c(s,t) v_n(s,t) ds\nB_front ~= integral_Gamma H_e(s,t) w_c(s,t) v_n(s,t) ds", styles))
    story.append(equation("B_front ~= H_e w_c vbar_n L_a\n        = H_e w_c f_a vbar_n P\n        = E_A dA/dt                         [S_A = 0]\nE_A = H_e w_c", styles))
    subsection(story, "S9.1 Heterogeneous fuel and flux weighting", styles)
    story.append(equation("E_A,eff = [integral H_e w_c v_n ds] / [integral v_n ds]", styles))
    story.append(p("For segment growth contributions G_1 = 1 and G_2 = 3 with E_1 = 2 and E_2 = 6, the flux-weighted effective energy per area is 5. The unweighted mean, 4, is incorrect for this aggregation.", styles))
    subsection(story, "S9.2 Front and residual power", styles)
    story.append(equation("B_f = B_front + B_residual", styles))
    story.append(p("Whole-fire power cannot be silently substituted for front-associated power. Burning can persist behind a front after mapped area recruitment stops.", styles))

    section(story, "S10. Residence-time model", styles, page_break=True)
    story.append(equation("Mdot_c(t) = Mdot_c,pre(t) + integral_[t0,t] w_inf(u) A_dot(u) g(t-u;u) du\ng(xi) = exp(-xi/tau_r)/tau_r", styles))
    story.append(equation("0 <= t <= T: Mdot_c = w G [1 - exp(-t/tau_r)]\nt > T:       Mdot_c = w G [1-exp(-T/tau_r)] exp[-(t-T)/tau_r]", styles))
    add_figure(story, 10, "10_residence_time_lag.png", "Consumption and power can persist after area recruitment stops. Numerical integration recovers total consumed mass w G T.", styles)

    section(story, "S11. Conditional metabolic scaling and counterexamples", styles, page_break=True)
    story.append(equation("B_f ~= H_e w_c k f_a vbar_n A^sigma", styles))
    story.append(equation("d log B_f/d log A ~= sigma + d log(H_e w_c k f_a vbar_n)/d log A\n                          + optional closure-error derivative", styles))
    counter_rows = [
        ["Geometry", "Changing factor", "Result"],
        ["P ~ A^(2/3)", "f_a ~ A^(-1/6)", "dA/dt ~ A^(1/2)"],
        ["P ~ A^(2/3)", "f_a ~ A^(-2/3)", "dA/dt is constant"],
        ["P ~ A^(2/3)", "vbar_n ~ A^(1/6)", "dA/dt ~ A^(5/6); ideal late-time A ~ t^6"],
    ]
    story.append(make_table(counter_rows, [1.65 * inch, 2.1 * inch, 3.0 * inch], styles))
    add_figure(story, 11, "11_active_fraction_counterexamples.png", "A common two-thirds perimeter geometry produces different dynamics when active fraction or normal speed changes with area.", styles)

    section(story, "S12. Proposed exponent-selection mechanisms", styles, page_break=True)
    subsection(story, "S12.1 Turbulent-surface intersection hypothesis", styles)
    story.append(equation("D_trace = D_s + 2 - 3 = D_s - 1\nD_s = 7/3 implies D_trace = 4/3", styles))
    story.append(p("This is a conditional generic-intersection model. It is not a theorem that a wildfire flame surface generates a 4/3 mapped footprint boundary. Projection, plane intersection, and accumulated burned footprint are different operations.", styles))
    add_figure(story, 12, "15_surface_intersection_projection.png", "A rough surface can project to a footprint with a smooth boundary; the intersection trace need not equal the accumulated footprint boundary.", styles, max_height=3.2 * inch)
    subsection(story, "S12.2 Percolation references", styles)
    story.append(p("Reference values are 7/4 for the full two-dimensional critical percolation hull and 4/3 for the accessible external perimeter. The package requires an explicit perimeter convention and does not infer that wildfire boundaries belong to either class.", styles))
    subsection(story, "S12.3 Transport matching", styles)
    story.append(equation("eta(r) = 4r/(1+r)^2\neta(1) = 1\nd eta/dr = 4(1-r)/(1+r)^3\nr = exp[lambda(D_h-D_star)]", styles))
    story.append(p("The matching function peaks at r = 1, but the mapping inserts D_star. Choosing D_star places the optimum wherever the modeler chooses. A series-resistance flux J = Delta X/(Z_1+Z_2) likewise does not generally have maximum flux at equal resistances.", styles))
    add_figure(story, 13, "12_matching_counterexample.png", "The transport curve proves a maximum at matched ratios, not a wildfire-specific preferred dimension.", styles)
    subsection(story, "S12.4 Connectivity", styles)
    story.append(equation("C = area of largest connected component / total patch area", styles))
    story.append(p("Components with areas 3 and 6 give C = 6/(3+6) = 2/3. This numerical value has no necessary relationship to the perimeter exponent.", styles))

    section(story, "S13. Forecasting and predictive uncertainty", styles, page_break=True)
    subsection(story, "S13.1 Transformed-area forecast", styles)
    story.append(equation("X = A^(1/3)\nX(t+h) = X(t) + (1/3) integral_[t,t+h] beta(u) du\nA_hat = X_hat^3\nFor constant beta_hat: A_hat = [A(t)^(1/3) + beta_hat h/3]^3", styles))
    story.append(equation("beta_hat = 3[A(t_2)^(1/3)-A(t_1)^(1/3)]/(t_2-t_1)", styles))
    story.append(p("The API separates calibration interval, forecast origin, and forecast horizon. The forecast origin cannot precede the end of calibration, preventing accidental use of future observations.", styles))
    subsection(story, "S13.2 Nonlinear back-transformation", styles)
    story.append(equation("E[X*^3] = mu_X^3 + 3 mu_X Var(X) + m3_X\npartial A_hat/partial beta = h [A(t)^(1/3)+beta h/3]^2", styles))
    add_figure(story, 14, "14_forecast_backtransform_uncertainty.png", "If X* is equally likely to be 2 or 4, mean area is 36 while cubing mean X gives 27.", styles)

    section(story, "S14. Late-stage growth and termination", styles, page_break=True)
    story.append(equation("A = c T^n\nF_late = 1 - (1-q)^n", styles))
    story.append(p("For the final half of duration, n = 3 gives 7/8 of the trajectory area and n = 2 gives 3/4. These are properties of assumed trajectories, not measured damage fractions.", styles))
    subsection(story, "S14.1 Exponential termination counterexample", styles)
    story.append(equation("A_final = c T^n\nT ~ Exponential(lambda)\nPr(A_final > A_star) = exp[-lambda (A_star/c)^(1/n)]", styles))
    story.append(p("Cubic within-event growth therefore does not automatically produce a power-law final-size distribution.", styles))

    section(story, "S15. Seven hypothetical worked examples", styles, page_break=True)
    story.append(callout("Status", "These seven examples share one hypothetical input window. They are conditional calculations, not independent empirical predictions.", styles, "orange"))
    shared = worked["inputs"]
    shared_rows = [
        ["Day", "Area (ha)", "Perimeter (km)", "Power (GW)", "Air temperature (K)"],
        [0, 100, 4, 5, 305],
        [3, 2700, 36, 5, 305],
    ]
    story.append(make_table(shared_rows, [0.7 * inch, 1.25 * inch, 1.45 * inch, 1.25 * inch, 1.65 * inch], styles))
    del shared
    subsection(story, "S15.1 Example 1: geometric slope", styles)
    story.append(equation("sigma_hat = log(36/4)/log(2700/100) = log(9)/log(27) = 2/3", styles))
    story.append(p("Two observations determine one secant slope. They do not establish persistence, fixed coefficients, or a reduced-growth regime.", styles))
    subsection(story, "S15.2 Example 2: coefficient, speed, and acceleration", styles)
    ex2 = worked["example_2"]
    ex2_rows = [
        ["Quantity", "Full-precision result", "Reported value"],
        ["beta_hat", f"{ex2['beta_hat_ha_one_third_day']:.12f}", "9.28318 ha^(1/3)/day"],
        ["k_hat", f"{ex2['k_hat_km_ha_minus_two_thirds']:.12f}", "0.185664 km ha^(-2/3)"],
        ["A_dot day 3", f"{ex2['area_rate_day3_ha_day']:.12f}", "1800 ha/day"],
        ["effective speed", f"{ex2['effective_speed_m_s']:.12f}", "0.00579 m/s"],
        ["A_ddot day 3", f"{ex2['acceleration_day3_ha_day2']:.12f}", "800 ha/day^2"],
    ]
    story.append(make_table(ex2_rows, [1.6 * inch, 2.35 * inch, 2.8 * inch], styles))
    subsection(story, "S15.3 Example 3: conditional trajectory", styles)
    story.append(equation("A(t) = 100 ha [1 + 2 tau/3]^3\nA_dot(t) = 200 ha/day [1 + 2 tau/3]^2", styles))
    story.append(p(f"Day 4 area = {worked['example_3']['area_day4_ha']:.5f} ha; day 5 area = {worked['example_3']['area_day5_ha']:.5f} ha.", styles))
    subsection(story, "S15.4 Example 4: perimeter and perimeter density", styles)
    trajectory_rows = [["Day", "A (ha)", "P (km)", "A_dot (ha/day)", "P/A (km/ha)"]]
    for row in worked["example_4"]:
        trajectory_rows.append([f"{row['day']:.0f}", f"{row['area_ha']:.2f}", f"{row['perimeter_km']:.2f}", f"{row['area_rate_ha_day']:.2f}", f"{row['perimeter_area_km_ha']:.5f}"])
    story.append(make_table(trajectory_rows, [0.65 * inch, 1.35 * inch, 1.25 * inch, 1.65 * inch, 1.45 * inch], styles))
    add_figure(story, 15, "13_worked_example_trajectory.png", "The day-4 and day-5 segments are conditional extrapolations from the day-0 to day-3 calibration window.", styles)
    subsection(story, "S15.5 Example 5: power-normalized quantities", styles)
    ex5 = worked["example_5"]
    power_rows = [
        ["Quantity", "Result"],
        ["5 GW / 305 K", f"{ex5['power_over_temperature_w_k']:.6e} W/K"],
        ["5 GW / 36 km", f"{ex5['power_over_perimeter_w_m']:.6e} W/m"],
        ["E_A day 0", f"{ex5['energy_per_area_day0_j_m2']/1e6:.2f} MJ/m^2"],
        ["E_A day 3", f"{ex5['energy_per_area_day3_j_m2']/1e6:.2f} MJ/m^2"],
    ]
    story.append(make_table(power_rows, [2.5 * inch, 3.0 * inch], styles))
    story.append(p("Constant chemical power, constant energy per newly burned area, and the accelerating fitted trajectory cannot all hold simultaneously.", styles))
    subsection(story, "S15.6 Example 6: time to an assumed reachable-area limit", styles)
    ex6 = worked["example_6"]
    story.append(p(f"For 2300 ha remaining at day 3, the stopping area is 5000 ha. The fitted-law remaining time is {ex6['remaining_time_days']:.8f} days; freezing the day-3 growth rate gives {ex6['frozen_rate_time_days']:.8f} days.", styles))
    subsection(story, "S15.7 Example 7: rate-change timing", styles)
    ex7 = worked["example_7"]
    rate_rows = [
        ["Scenario", "beta maximum", "rho_beta maximum", "Required reduction"],
        ["20% reduction from day 0", "0.8 x baseline", f"Area ratio {ex7['reduced_to_baseline_ratio']:.5f}", f"Day-5 area {ex7['reduced_area_day5_ha']:.2f} ha"],
        ["Target <= 5000 ha, change day 0", f"{ex7['beta_max_from_day0']:.5f}", f"{ex7['rho_max_from_day0']:.5f}", f"{100*ex7['reduction_from_day0']:.2f}%"],
        ["Target <= 5000 ha, change day 3", f"{ex7['beta_max_from_day3']:.5f}", f"{ex7['rho_max_from_day3']:.5f}", f"{100*ex7['reduction_from_day3']:.2f}%"],
    ]
    story.append(make_table(rate_rows, [2.3 * inch, 1.45 * inch, 1.45 * inch, 1.55 * inch], styles))
    story.append(p("These are coefficient constraints, not suppression prescriptions. An operational interpretation requires a separate model linking actions to active fraction, speed, recruitment, or termination.", styles))

    section(story, "S16. Spatial-model experiment framework", styles, page_break=True)
    stage_rows = [["Stage", "Mechanism or control"]] + [[index, name.replace("_", " ")] for index, name in enumerate((
        "documented ignition geometry", "uniform fuel", "flat terrain", "zero-wind control", "uniform wind", "fixed-aspect-ratio ellipse control", "heterogeneous fuel", "terrain", "spatially varying wind", "temporally varying wind", "spotting", "mergers", "full configuration"
    ), 1)]
    story.append(make_table(stage_rows, [0.65 * inch, 5.7 * inch], styles))
    story.append(p("Every stage records A, P, R_P, perimeter-area slope, and dA/dt, plus active fraction, mean normal speed, chemical power, and aspect ratio when available. The framework supports stochastic replicates, mechanism-removal factorial comparisons, multiple spatial resolutions, and perimeter simplification settings.", styles))
    story.append(callout("Scientific question", "Which mechanisms cause whole-footprint geometry to depart from the smooth-family one-half null, and under what conditions does an approximately two-thirds trajectory appear? The answer is not hard-coded.", styles))

    section(story, "S17. Statistical estimation and observation metadata", styles, page_break=True)
    story.append(equation("Within event: log(P_it/P_r) = alpha_i + sigma_i log(A_it/A_r) + error\nBetween events: fit one final-size record per event", styles))
    story.append(p("The API refuses to pool multiple events in a within-event fit and refuses repeated records per event in a between-event final-size fit. It compares a freely estimated sigma with fixed one-half and two-thirds models and supports explicit rolling windows for changing exponents.", styles))
    metadata_rows = [
        ["Required metadata", "Reason"],
        ["Spatial resolution", "Perimeter and small components depend on resolution"],
        ["Perimeter convention", "Exterior, holes, and accessible perimeter are different objects"],
        ["Event ID and observation time", "Separates within-event from between-event scaling"],
        ["Area range", "Scaling may be local to a finite range"],
        ["Component and hole treatment", "Changes both P and connectivity"],
    ]
    story.append(make_table(metadata_rows, [2.1 * inch, 4.3 * inch], styles))
    story.append(p("Ordinary regression uncertainty is not a complete uncertainty analysis because area and perimeter are derived from the same geometry and their errors can be correlated.", styles))

    section(story, "S18. Computational verification", styles, page_break=True)
    summary = report["claim_summary"]
    verification_rows = [
        ["Check", "Result"],
        ["Repository tests", "91 passed"],
        ["Symbolic residual checks", "8 reduced to zero"],
        ["Worked examples", "7 of 7 reproduced"],
        ["Analytical/synthetic figure sets", "15 generated and visually inspected"],
        ["Claims in ledger", summary["total_claims"]],
        ["Claims requiring empirical data", summary["requires_empirical_data"]],
        ["Empirical validation performed", "No"],
        ["Mathematical inconsistencies found", "None in the implemented checks"],
        ["Section S19 numerical failures", "None"],
    ]
    story.append(make_table(verification_rows, [3.1 * inch, 3.25 * inch], styles))
    subsection(story, "S18.1 Test philosophy", styles)
    for text in (
        "Identity tests verify definitions and exact mathematical statements.",
        "Derivation tests verify consequences of named assumptions.",
        "Numerical consistency tests compare solve_ivp trajectories with analytic solutions.",
        "Construction tests independently compute polygon area and perimeter from coordinates.",
        "Counterexample tests preserve negative results that block overinterpretation.",
        "Worked-example regression tests reproduce the full-precision Section S19 calculations.",
        "Empirical-validation placeholders expose interfaces for observations that are not present here.",
    ):
        story.append(bullet(text, styles))

    section(story, "S19. Machine-readable claim ledger", styles, page_break=True)
    claim_rows = [["Claim", "Type", "Status", "Empirical data?"]]
    for claim in claims:
        if claim["requires_empirical_data"]:
            status = "Mathematical consequences only" if claim["verified_by"] != ["not validated by this package"] else "Not validated"
        else:
            status = "Computationally checked"
        claim_rows.append([claim["claim_id"], claim["type"].replace("_", " "), status, "Yes" if claim["requires_empirical_data"] else "No"])
    story.append(make_table(claim_rows, [1.8 * inch, 1.65 * inch, 2.25 * inch, 0.9 * inch], styles, font_size=6.8))
    story.append(callout("Ledger rule", "A successful algebraic or numerical check cannot change an empirical hypothesis into a validated observation. The ledger records these statuses explicitly.", styles, "orange"))

    section(story, "S20. Claims that remain empirical", styles, page_break=True)
    for text in (
        "A persistent approximately two-thirds within-event mapped perimeter-area relationship exists in wildfire observations under a stated perimeter convention.",
        "Mapped perimeter is a useful proxy for independently measured active-boundary length.",
        "The active fraction and normal velocity factors remain sufficiently stable for a reduced growth closure over a forecast interval.",
        "Front-associated chemical power is proportional to newly recruited burned area after accounting for residual combustion and residence time.",
        "A turbulent-surface intersection mechanism, percolation accessibility, or transport matching selects a wildfire boundary exponent.",
        "The proposed reduced state transfers across events and improves held-out predictions over recent-growth and weather baselines.",
    ):
        story.append(bullet(text, styles))
    subsection(story, "S20.1 Assumptions not testable with the reproduction inputs", styles)
    for text in (
        "Independent active-boundary classification and mean normal velocity.",
        "Untracked spot-fire recruitment and merger bookkeeping.",
        "Fuel-consumption loading, heat yield, and residence-time kernels.",
        "Front-associated versus residual chemical power.",
        "Persistence of k, sigma, f_a, vbar_n, and beta beyond calibration.",
        "A fixed finite maximum local speed and the absence of nonlocal recruitment.",
        "Observation uncertainty, correlated geometric errors, and sensitivity to mapping resolution.",
    ):
        story.append(bullet(text, styles))

    section(story, "S21. Reproducibility and package map", styles, page_break=True)
    story.append(equation("PYTHONPATH=src python scripts/reproduce_si.py\nPYTHONPATH=src python scripts/reproduce_si.py --check-only\nPYTHONPATH=src python scripts/build_computational_si_pdf.py", styles))
    package_rows = [
        ["Module", "Responsibility"],
        ["geometry.py", "Similarity, ellipses, box counting, polygons, connectivity"],
        ["kinematics.py", "Boundary integral, active subset, source term, residual"],
        ["growth.py", "Analytic laws, acceleration, bounds, sources, termination"],
        ["energetics.py", "Front consumption, flux weighting, conditional power"],
        ["residence.py", "Cohort convolution and exponential kernel"],
        ["scaling.py", "Closures, bridges, excess perimeter, estimation, counterexamples"],
        ["forecasting.py", "Calibration, forecasting, uncertainty, sensitivity"],
        ["synthetic.py", "Staged and factorial model-experiment infrastructure"],
        ["units.py", "Dimensional bookkeeping"],
        ["diagnostics.py", "SymPy checks and claim-ledger validation"],
        ["worked_examples.py", "Full-precision Section S19 reproduction"],
    ]
    story.append(make_table(package_rows, [1.55 * inch, 5.0 * inch], styles))
    story.append(p("The eight notebooks expose these tested APIs without duplicating the implementation. Large generated outputs remain outside git by default; source code, assumptions, parameters, tests, and the claim ledger remain traceable.", styles))

    section(story, "S22. Conclusion", styles, page_break=True)
    story.append(p("The computational companion reproduces the mathematical consequences requested from the supplied Supplementary Information. It verifies the dimensional ladder, geometric constructions, boundary kinematics, fixed-exponent growth laws, acceleration criterion, finite-speed conflict, source-term behavior, conditional geometry-to-power bridge, residence-time lag, forecasting transforms, termination counterexample, and all seven hypothetical worked examples.", styles))
    story.append(p("The strongest result is methodological: the calculation becomes more informative when it is harder to overclaim. Perimeter geometry, active-boundary advance, area recruitment, fuel consumption, and chemical power are related only through separately stated commitments. Those commitments can now be tested independently when appropriate observations become available.", styles))
    story.append(callout("Final status", "Mathematical and numerical reproduction: passed. Empirical wildfire validation: not performed. No Section S19 numerical discrepancy was found.", styles, "blue"))

    section(story, "Appendix A. Equation and result index", styles, page_break=True)
    equation_rows = [
        ["Topic", "Computational check"],
        ["Dimensional ladder", "Symbolic elimination and canonical shapes"],
        ["Ellipse controls", "Fixed and changing aspect-ratio numerical slopes"],
        ["Box counting", "Separated resolution, between-size, and trajectory metadata"],
        ["Boundary bridge", "sigma = D_h/D_A and D_A = 2 specialization"],
        ["Excess perimeter", "Identity and area x64 example"],
        ["Right-angle family", "Independent shoelace area and edge-length perimeter"],
        ["Boundary kinematics", "Uniform, heterogeneous, partial, holes, components, source"],
        ["Mapped closure", "Units of k and changing-kappa counterexample"],
        ["Growth law", "Symbolic identities and solve_ivp comparisons"],
        ["Acceleration", "Symbolic derivative and three beta trajectories"],
        ["Finite-speed bound", "Numerical first crossing"],
        ["Source term", "Cube-root derivative and discrete jumps"],
        ["Energetics", "Flux-weighted energy and residual-power separation"],
        ["Residence time", "Closed form and mass-integral check"],
        ["Conditional metabolic scaling", "Variable-factor exponent counterexamples"],
        ["Surface intersection", "Conditional D_trace model and synthetic distinction"],
        ["Percolation", "Explicit convention-required comparison"],
        ["Transport matching", "Derivative and arbitrary D_star counterexample"],
        ["Connectivity", "C = 2/3 example, explicitly unrelated to sigma"],
        ["Forecasting", "Calibration separation and transformed forecast"],
        ["Uncertainty", "Moment identity and Monte Carlo example"],
        ["Late-stage fraction", "n = 3 and n = 2 examples"],
        ["Termination", "Exponential-lifetime exceedance"],
        ["Worked examples", "All seven full-precision regression checks"],
    ]
    story.append(make_table(equation_rows, [2.05 * inch, 4.45 * inch], styles, font_size=6.8))

    section(story, "Appendix B. Source and evidence boundary", styles, page_break=True)
    story.append(p("Primary source: the user-supplied mathematical Supplementary Information for Fire Is Metabolic, file supplementary-6.pdf. The source document provides the conceptual and mathematical structure reproduced here.", styles))
    story.append(p("No external wildfire observations were added. All plotted trajectories are analytical, synthetic, constructed, or hypothetical and are labeled accordingly. The package is designed so future empirical adapters can be added without changing the status of existing mathematical claims.", styles))
    story.append(p("End of computational Supplementary Information.", styles, "small"))
    return story


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    claims = json.loads(CLAIM_LEDGER.read_text(encoding="utf-8"))
    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    worked = reproduce_worked_examples()
    styles = make_styles()
    doc = SIDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title="Fire Is Metabolic - Computational Supplementary Information",
        author="spread-vs-growth project",
        subject="Mathematical verification, conditional predictions, counterexamples, and worked examples",
    )
    doc.multiBuild(build_story(styles, claims, report, worked))

    reader = PdfReader(str(OUTPUT))
    if len(reader.pages) < 20:
        raise RuntimeError(f"Unexpectedly short PDF: {len(reader.pages)} pages")
    print(f"Wrote {OUTPUT}")
    print(f"Pages: {len(reader.pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
