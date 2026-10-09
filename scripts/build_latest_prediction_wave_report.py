#!/usr/bin/env python3
"""Build the integrated FIRED prediction, transport, and constraint report."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/fire_prediction_geometry_constraints_evidence_report.pdf"
LATENT = ROOT / "outputs/latent_constraint_validation"
HALF = ROOT / "outputs/half_vs_two_thirds_constraint_test"
INTEGRATED = ROOT / "outputs/integrated_geometry_transport"

NAVY = colors.HexColor("#16324F")
BLUE = colors.HexColor("#6495ED")
RED = colors.HexColor("#B3261E")
GREEN = colors.HexColor("#2A8C5A")
GOLD = colors.HexColor("#D28B26")
LIGHT = colors.HexColor("#EEF3F7")
INK = colors.HexColor("#222222")


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="ReportTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=NAVY, alignment=TA_LEFT, spaceAfter=14))
    base.add(ParagraphStyle(name="Subtitle", parent=base["Normal"], fontSize=12, leading=17, textColor=colors.HexColor("#46535E"), spaceAfter=18))
    base.add(ParagraphStyle(name="H1x", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, spaceBefore=6, spaceAfter=10))
    base.add(ParagraphStyle(name="H2x", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=GREEN, spaceBefore=8, spaceAfter=6))
    base.add(ParagraphStyle(name="Bodyx", parent=base["BodyText"], fontSize=9.4, leading=13.2, textColor=INK, spaceAfter=7))
    base.add(ParagraphStyle(name="Smallx", parent=base["BodyText"], fontSize=7.6, leading=10.2, textColor=colors.HexColor("#3E4A52"), spaceAfter=4))
    base.add(ParagraphStyle(name="Callout", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=NAVY, backColor=LIGHT, borderColor=BLUE, borderWidth=0.8, borderPadding=10, spaceBefore=6, spaceAfter=10))
    base.add(ParagraphStyle(name="VerdictGood", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=GREEN, spaceAfter=5))
    base.add(ParagraphStyle(name="VerdictCaution", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=RED, spaceAfter=5))
    base.add(ParagraphStyle(name="Captionx", parent=base["BodyText"], fontSize=7.5, leading=10, textColor=colors.HexColor("#4D5963"), alignment=TA_CENTER, spaceBefore=3, spaceAfter=10))
    base.add(ParagraphStyle(name="Codex", parent=base["Code"], fontName="Courier", fontSize=7.2, leading=9.2, backColor=colors.HexColor("#F5F7F9"), borderPadding=7, spaceAfter=8))
    return base


S = styles()


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, S[style])


def table(rows, widths=None, font_size=7.5):
    converted = [[p(str(cell), "Smallx") for cell in row] for row in rows]
    result = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BAC5CE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7F9")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]))
    return result


def figure(path: Path, caption: str, width=7.0 * inch):
    image = Image(str(path), width=width, height=width * 0.60)
    return KeepTogether([image, p(caption, "Captionx")])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD4DB"))
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#5C6871"))
    canvas.drawString(0.65 * inch, 0.35 * inch, "FIRED prediction, geometry, transport, and latent realization evidence")
    canvas.drawRightString(7.85 * inch, 0.35 * inch, f"{doc.page}")
    canvas.restoreState()


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    latent_report = json.loads((LATENT / "run_report.json").read_text())
    half_report = json.loads((HALF / "run_report.json").read_text())
    integrated_report = json.loads((INTEGRATED / "run_report.json").read_text())
    hazards = pd.read_csv(LATENT / "constraint_hazard_models.csv")
    predictions = pd.read_csv(LATENT / "constraint_prediction_metrics.csv")
    attractor = pd.read_csv(LATENT / "attractor_shock_sensitivity.csv")
    ot = pd.read_csv(LATENT / "ot_constraint_relationship.csv")
    half_relation = pd.read_csv(HALF / "relative_advantage_vs_residual.csv")
    paired = pd.read_csv(INTEGRATED / "paired_model_comparisons.csv")

    doc = BaseDocTemplate(str(OUT), pagesize=letter, rightMargin=.65*inch, leftMargin=.65*inch, topMargin=.62*inch, bottomMargin=.72*inch, title="Fire Prediction Geometry And Latent Constraints: Integrated Evidence Report", author="spread-vs-growth reproducible analysis")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
    story = []

    story += [Spacer(1, .25*inch), p("Fire Prediction, Geometry, Transport, and Latent Realization", "ReportTitle"), p("Integrated evidence report for the latest FIRED and FireProof validation wave | 9 October 2026", "Subtitle")]
    story += [p("Bottom line", "H1x"), p("We are good at estimating near-term growth potential and useful at short-horizon mapped-area prediction. We are only modest at predicting a large future growth deficit, and we are not yet good at precise realized long-horizon outcome or death timing. The new latent-constraint model improves detection more than point prediction.", "Callout")]
    story += [p("The proposed explanation for the one-half result did not survive its falsification test. One-half remains competitive when fires grow near model-implied potential; its advantage is not concentrated in the strongest negative realization residuals.", "VerdictCaution")]
    story += [table([
        ["Capability", "Current evidence", "Verdict"],
        ["Near-term future area", "Origin-time geometry and dynamics substantially beat recent-growth carry-forward", "Useful"],
        ["Model-implied growth potential", "Selected without held-out outcomes; residuals are stable enough for analysis", "Useful, not a physical maximum"],
        ["Large growth-deficit risk", "Geometry Brier 0.0866 vs 0.0905 constant", "Modest skill"],
        ["Long-horizon realized area", "Hazard correction does not beat unadjusted expected growth at 42 days", "Not yet reliable"],
        ["Death timing", "Deficits mark impending termination retrospectively; early warning remains weak", "Weak"],
        ["Causal attribution", "FIRED cannot separate B from K or name suppression/barrier causes", "Not identifiable"],
    ], widths=[1.55*inch, 3.9*inch, 1.55*inch])]
    story += [Spacer(1, 8), p("Scope", "H2x"), p(f"The locked cohort contains {latent_report['events']:,} FIRED events: development 2001-2012, calibration 2013-2015, and held-out 2016-2020. The corrected transport sample contains {integrated_report['real_transport_transitions']:,} transitions from {integrated_report['real_transport_events']:,} events. All uncertainty and model-selection decisions preserve whole-fire and temporal separation.")]
    story.append(PageBreak())

    story += [p("1. What changed in this wave", "H1x")]
    story += [p("This wave joined four previously separate questions: whether mapped geometry restores toward two-thirds, whether real footprint reorganization adds state information, whether potential and realized growth should be separated, and whether unresolved deficits explain the predictive success of one-half.")]
    story += [table([
        ["Layer", "New work", "Scientific role"],
        ["Integrated geometry + OT", "Corrected outcome-blind 941-fire sample; 8,667 transitions; area-matched dilation null", "Tests spatial reorganization beyond ordinary geometry"],
        ["Latent realization", "M_real = B K A^(2/3), origin-safe expected growth, residual q", "Separates expected potential from realized departure without attributing cause"],
        ["Prospective hazard", "H0-H4 deficit risk models and mixture forecasts", "Tests whether departures can be anticipated"],
        ["One-half falsification", "D = loss(1/2)-loss(2/3) as a function of q", "Tests whether constraints rescue the two-thirds interpretation"],
        ["FireProof", "Bounds, product identifiability, admissible futures, bounded shocks", "Makes assumptions and failure boundaries explicit"],
    ], widths=[1.35*inch, 3.0*inch, 2.65*inch])]
    story += [p("Interpretive vocabulary", "H2x"), p("Observed: mapped growth was lower than expected. Detected: a statistically unusual residual or change point occurred. Constraint-like: the trajectory is consistent with an unresolved realization process. Attributed: independent evidence names the cause. FIRED alone generally stops at constraint-like.")]
    story += [p("The observable previously written K_obs=M/A^(2/3) is now called realized effective coupling. Under the extension it equals B K; area growth cannot identify B and K separately.", "Callout")]
    story.append(PageBreak())

    story += [p("2. Integrated geometry and transport", "H1x")]
    story += [figure(INTEGRATED / "figure1_integrated_geometry_transport.png", "Figure 1. Locked geometry-transport validation. Reorganization is measured against an area-matched isotropic dilation null.")]
    story += [p("Departure from two-thirds predicts more spatial reorganization, but reorganization does not consistently restore mapped geometry toward two-thirds. OT adds small held-out future-coupling gains beyond geometry for several origins and horizons, but the effect is incremental rather than transformative.")]
    relevant = paired[(paired.snapshot_day == 5) & (paired.model == "geometry_plus_OT") & (paired.lead_days.isin([1, 3, 5, 7, 14, 21, 42]))]
    rows = [["Lead", "Paired K-MAE difference", "95% interval", "Interpretation"]]
    for row in relevant.itertuples(index=False):
        rows.append([f"{row.lead_days} d", f"{row.mean_paired_K_mae_difference:.4f}", f"[{row.ci95_lower:.4f}, {row.ci95_upper:.4f}]", "OT improves" if row.ci95_upper < 0 else "uncertain"])
    story += [table(rows, widths=[.7*inch, 1.5*inch, 1.75*inch, 2.2*inch])]
    story += [p("What this means", "H2x"), p("Spatial state matters, but R is not a mechanism by itself. The formal result that R can narrow admissible futures requires an empirically supplied R-indexed bound; the data support only a modest predictive closure.")]
    story.append(PageBreak())

    story += [p("3. Potential versus realized growth", "H1x"), figure(LATENT / "figure1_latent_constraint_validation.png", "Figure 2. Expected and realized growth, residual tail, forecast impact, attractor sensitivity, and mapped boundary productivity.")]
    story += [p(f"The analysis generated {latent_report['rows']:,} origin-horizon intervals from {latent_report['events']:,} fires. Held-out median q was {latent_report['median_q']:.3f}; the first percentile was {latent_report['most_negative_tail_q01']:.3f}. This heavy negative tail is real as a prediction residual, but its physical cause is not identified.")]
    hz_rows = [["Hazard", "Sample", "n", "Brier", "Log score"]]
    for row in hazards.itertuples(index=False):
        if pd.notna(row.brier):
            hz_rows.append([row.model, row.sample, f"{int(row.n):,}", f"{row.brier:.4f}", f"{row.log_score:.4f}"])
    story += [table(hz_rows, widths=[1.55*inch, 1.55*inch, .75*inch, .8*inch, .8*inch])]
    story += [p("Geometry has modest prospective value for deficit risk. The matched OT model is reported with a matched geometry comparator because the full-sample and OT-sample scores are not directly comparable.", "Smallx")]
    story.append(PageBreak())

    story += [p("4. Does the hazard improve realized predictions?", "H1x")]
    piv = predictions[predictions.lead_days.isin([1, 3, 7, 14, 28, 42])].pivot(index="lead_days", columns="prediction_model", values="future_area_mae_log")
    pred_rows = [["Lead", "Recent growth", "Expected growth", "Constant hazard", "Geometry hazard"]]
    for lead, row in piv.iterrows():
        pred_rows.append([f"{lead} d", f"{row.get('P0_recent_growth', float('nan')):.3f}", f"{row.get('P1_model_implied_growth', float('nan')):.3f}", f"{row.get('P2_constant_hazard', float('nan')):.3f}", f"{row.get('P4_geometry_hazard', float('nan')):.3f}"])
    story += [table(pred_rows, widths=[.8*inch, 1.25*inch, 1.25*inch, 1.25*inch, 1.25*inch])]
    story += [p("The expected-growth model is the major gain. The hazard correction helps at one day, is roughly neutral at intermediate horizons, and is worse at 28-42 days. This is not a successful long-horizon point-forecast extension.", "VerdictCaution")]
    story += [p("The hazard still has scientific value: it provides a probability that the next interval belongs to the negative tail, which can widen uncertainty even when the posterior mean should remain close to the unadjusted model.")]
    story += [p("Termination", "H2x"), p("Constraint-like intervals are enriched immediately before mapped termination: at seven days the retrospective termination rate is 90.8% versus 48.8%. This says the residual detects a dying trajectory after the future interval is observed; it does not yet solve origin-time death prediction.")]
    story.append(PageBreak())

    story += [p("5. The one-half versus two-thirds falsification", "H1x"), figure(HALF / "figure1_half_vs_two_thirds_constraint_test.png", "Figure 3. Relative fixed-center forecast advantage versus realization deficit, slope state, age, filtering, boundary productivity, and reproducible counterexamples.")]
    story += [p(f"The exact-match sample has {half_report['n']:,} transitions from {half_report['n_fires']:,} held-out fires. Overall Spearman association between q and D is {half_report['spearman_q_D']:.3f}. Near potential, mean D is {half_report['near_potential_mean_D']:.4f} and one-half wins {100*half_report['near_potential_half_win_rate']:.1f}%. In the strongest deficit decile, mean D is {half_report['strong_deficit_mean_D']:.4f} and one-half wins {100*half_report['strong_deficit_half_win_rate']:.1f}%.")]
    story += [p("This rejects the simple constraint-mixture explanation. The pattern is not merely weak; its aggregate direction is opposite the proposed rescue. Lead-specific behavior varies, so this does not prove a physical one-half attractor. It means only that unresolved growth deficits are not a sufficient explanation for one-half's predictive performance.", "Callout")]
    rel_rows = [["Lead", "n", "Mean D", "Near-potential D", "Near-potential half win"]]
    for row in half_relation.itertuples(index=False):
        rel_rows.append([f"{row.lead_days} d", f"{int(row.n):,}", f"{row.mean_D:.3f}", f"{row.near_potential_mean_D:.3f}", f"{100*row.near_potential_half_win_rate:.1f}%"])
    story += [table(rel_rows, widths=[.75*inch, .75*inch, 1.0*inch, 1.4*inch, 1.5*inch])]
    story.append(PageBreak())

    story += [p("6. Attractor, OT timing, and observation effects", "H1x")]
    at_rows = [["Partition", "Method", "Restoring strength", "n"]]
    for row in attractor.itertuples(index=False):
        if row.partition == "held_out":
            at_rows.append([row.partition, row.method, f"{row.restoring_strength:.3f}", f"{int(row.n):,}"])
    story += [table(at_rows, widths=[1.0*inch, 3.2*inch, 1.3*inch, .9*inch])]
    story += [p("The naive fixed-center coefficient looks restoring, but Huber weighting nearly eliminates it. Excluding development-defined deficit extremes increases the naive coefficient rather than stabilizing a robust universal attractor. Measurement error and perimeter definition remain sufficient alternative explanations.")]
    ot_rows = [["Timing test", "Partition", "n", "Spearman rho"]]
    for row in ot.itertuples(index=False):
        if row.partition == "held_out":
            ot_rows.append([row.analysis, row.partition, f"{int(row.n):,}", f"{row.spearman_rho:.3f}"])
    story += [table(ot_rows, widths=[2.9*inch, 1.0*inch, .9*inch, 1.1*inch])]
    story += [p("The contemporaneous association is substantial; the prospective prior-R association is negligible. Geometry and OT can describe a changed growth mode once it is happening, but this implementation does not show useful spatial lead time.")]
    story.append(PageBreak())

    story += [p("7. Formal results and identifiability", "H1x")]
    story += [p("FireProof now distinguishes endogenous potential, realization, and spatial observation. The new Lean module proves the following without assigning a physical meaning to B:")]
    story += [table([
        ["Formal result", "Meaning"],
        ["0 <= M_real <= M_pot", "Conditional on 0<=B<=1 and nonnegative potential factors"],
        ["B=1 recovers M_pot", "The original model is the unconstrained special case"],
        ["M_real/A^(2/3)=BK", "The normalized observable is realized coupling"],
        ["(B,K)=(1/2,2) and (1,1) agree", "Area growth cannot identify B and K separately"],
        ["Tighter B bounds narrow futures", "External information can make prediction sets smaller"],
        ["Restoration under bounded shocks", "Restoration is conditional, not universal"],
    ], widths=[2.3*inch, 4.6*inch])]
    story += [p("Which theorems change?", "H2x"), p("Pure scaling identities and potential-growth algebra remain unchanged. A theorem used as a realized trajectory forecast must assume B=1, observe B, or carry an interval for B. Unrestricted shocks invalidate universal restoration claims.")]
    story += [p("Attribution", "H2x"), p("No Lean type or empirical label equates B with suppression, water, roads, urban land, or fuel discontinuity. Those are hypotheses for future external validation.")]
    story.append(PageBreak())

    story += [p("8. Are we good at prediction yet?", "H1x")]
    story += [p("Yes for some targets and horizons; no for the broad claim.", "Callout")]
    story += [table([
        ["Target", "Assessment", "Why"],
        ["1-7 day mapped area", "Good research-grade skill", "Geometry/dynamics models improve materially over naive carry-forward"],
        ["Future realized coupling", "Moderate", "Predictable from recent state; geometry and OT add small gains"],
        ["Maximum/potential course", "Promising", "The expected-growth trajectory captures capacity better than realized interruptions"],
        ["Large deficit probability", "Modest", "Proper scores improve, calibration remains shallow"],
        ["Final realized area", "Limited", "External/latent realization and long horizon uncertainty accumulate"],
        ["Exact death timing", "Poor", "Abrupt endings and reactivation are not captured precisely"],
        ["Mechanism attribution", "Unavailable", "FIRED lacks independent forcing, fuel, barrier, and suppression labels"],
    ], widths=[1.55*inch, 1.55*inch, 3.8*inch])]
    story += [p("The fair interpretation is that the models estimate how much the fire is capable of doing better than they estimate how much is ultimately realized. That is a real predictive achievement, but it should be reported as potential or expected growth skill, not complete event prognosis.")]
    story += [p("What is missing", "H2x"), p("The next predictive gains likely require prospective fuel connectivity and prior-burn layers, fire-scale weather rather than centroid weather, active-boundary observations, suppression/incident records, and an explicit satellite observation model. These additions should be tested as independent inputs, not inferred post hoc from residuals.")]
    story.append(PageBreak())

    story += [p("9. Claims safe for the SI", "H1x")]
    story += [table([
        ["Claim", "Status"],
        ["Mapped geometry contains prospective growth information", "Supported"],
        ["Realized coupling is predictable from past state", "Supported"],
        ["OT adds small information beyond geometry", "Partially supported"],
        ["FIRED detects unusually negative realization residuals", "Supported retrospectively"],
        ["Geometry modestly predicts deficit risk", "Partially supported"],
        ["Latent hazards improve long-range point forecasts", "Not supported"],
        ["Two-thirds is a universal geometric attractor", "Not supported"],
        ["Constraints explain one-half performance", "Not supported"],
        ["One-half is proven physical", "Not supported"],
        ["FIRED identifies suppression or barriers", "Not identifiable"],
    ], widths=[5.2*inch, 1.7*inch])]
    story += [p("Recommended manuscript wording", "H2x"), p("Past mapped geometry and dynamics predict near-term realized growth, while residual variation and abrupt termination remain only partly predictable. A latent realization factor provides a coherent account of the gap between model-implied expected growth and observed growth, but FIRED does not identify its cause. Accounting for negative realization residuals does not restore a predictive advantage for a fixed two-thirds geometric attractor.")]
    story.append(PageBreak())

    story += [p("10. Reproducibility and output inventory", "H1x")]
    commands = """PYTHONPATH=src ../cubedynamics/.venv/bin/python \\
  scripts/extract_fired_transport_metrics.py
PYTHONPATH=src ../cubedynamics/.venv/bin/python \\
  scripts/run_integrated_geometry_transport.py
PYTHONPATH=src ../cubedynamics/.venv/bin/python \\
  scripts/run_latent_constraint_validation.py
PYTHONPATH=src ../cubedynamics/.venv/bin/python \\
  scripts/run_half_vs_two_thirds_constraint_test.py
cd FireProof && lake build && bash scripts/audit.sh"""
    story += [p("Core commands", "H2x"), Preformatted(commands, S["Codex"])]
    story += [p("Primary data products", "H2x"), table([
        ["Directory", "Contents"],
        ["outputs/integrated_geometry_transport", "Transport transitions, attractor/OT models, paired forecasts, sensitivity analyses, figures"],
        ["outputs/latent_constraint_validation", "Expected growth, residuals, candidate events, hazards, termination, OT timing, attractor sensitivity, figures"],
        ["outputs/half_vs_two_thirds_constraint_test", "Matched losses, q-D tests, filtering, slope/productivity/perimeter diagnostics, examples, figures"],
        ["FireProof/FireProof/Realization.lean", "Realization bounds, product identifiability, admissible futures, bounded-shock result"],
    ], widths=[2.3*inch, 4.6*inch])]
    story += [p("Design protections", "H2x"), p("The cohort, calendar split, local-slope estimator, origins, horizons, and development/calibration thresholds are recorded in design_lock.json files. Potential-growth selection excludes held-out outcomes; constraint thresholds are lead-specific and locked before held-out evaluation; cause labels are never assigned from FIRED residuals.")]
    story.append(PageBreak())

    story += [p("Appendix A. Detectability boundary", "H1x"), table([
        ["Quantity", "Before", "At onset", "After", "Cause?"],
        ["Area-growth deficit", "probabilistic", "partial", "yes", "no"],
        ["Geometry change", "weak", "partial", "yes", "no"],
        ["OT reorganization", "weak", "yes", "yes", "no"],
        ["Realized coupling decline", "forecast only", "yes", "yes", "no"],
        ["External realization B", "latent", "latent", "latent", "no"],
        ["Suppression/water/urban barrier", "no", "no", "no", "requires external data"],
    ], widths=[2.2*inch, 1.25*inch, 1.25*inch, 1.25*inch, 1.25*inch])]
    story += [p("Appendix B. External validation roadmap", "H1x"), p("Join trajectory-derived candidate events prospectively to surface water, impervious land, roads, previous burns, fuels, suppression records, and higher-frequency active-fire observations. The decisive test is whether an origin-time detector predicts an independently observed encounter, and whether adding that layer improves held-out realized-area and death predictions beyond geometry, weather, and recent growth.")]
    story += [p("No claim in this report attributes an event to suppression or a physical barrier without such independent evidence.", "VerdictCaution")]

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
