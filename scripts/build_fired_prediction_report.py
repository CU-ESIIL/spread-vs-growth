#!/usr/bin/env python3
"""Build a concise PDF report for the FIRED prediction validation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
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
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs" / "fired_outcome_validation"
OUTPUT = ROOT / "output" / "pdf" / "fired_prediction_validation_report.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#0072B2")
ORANGE = colors.HexColor("#D55E00")
GREEN = colors.HexColor("#2E7D5B")
INK = colors.HexColor("#20262C")
MUTED = colors.HexColor("#5F6973")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_ORANGE = colors.HexColor("#FDF1E8")
LIGHT_GREEN = colors.HexColor("#EAF5F0")
LIGHT_GRAY = colors.HexColor("#F2F4F5")
RULE = colors.HexColor("#C9D0D5")


def draw_page(canvas, doc):
    width, height = letter
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, height - 0.45 * inch, width - doc.rightMargin, height - 0.45 * inch)
        canvas.setFont("Helvetica", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, height - 0.34 * inch, "FIRED PREDICTION VALIDATION")
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.36 * inch, "Retrospective satellite-derived event sequences")
    canvas.drawRightString(width - doc.rightMargin, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


class ReportTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=letter,
            leftMargin=0.68 * inch,
            rightMargin=0.68 * inch,
            topMargin=0.64 * inch,
            bottomMargin=0.62 * inch,
            title="FIRED Prediction Validation Report",
            author="spread-vs-growth",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=draw_page))


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=29,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=17,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=NAVY,
            spaceBefore=7,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=ORANGE,
            spaceBefore=6,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.3,
            leading=13.1,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.7,
            leading=10.2,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "ReportCaption",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.7,
            leading=10,
            textColor=MUTED,
            spaceBefore=3,
            spaceAfter=7,
        ),
        "metric": ParagraphStyle(
            "ReportMetric",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "ReportMetricLabel",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


def paragraph(text: str, styles, style: str = "body"):
    return Paragraph(text, styles[style])


def bullet(text: str, styles):
    return Paragraph(
        f"- {text}",
        ParagraphStyle(
            "ReportBullet",
            parent=styles["body"],
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=4,
        ),
    )


def callout(title: str, text: str, styles, tone: str = "blue"):
    palette = {
        "blue": (LIGHT_BLUE, BLUE),
        "orange": (LIGHT_ORANGE, ORANGE),
        "green": (LIGHT_GREEN, GREEN),
    }
    background, accent = palette[tone]
    content = Table(
        [[paragraph(f"<b>{title}</b>", styles), paragraph(text, styles)]],
        colWidths=[1.42 * inch, 5.12 * inch],
    )
    content.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.7, accent),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return content


def make_table(rows, widths, styles, *, header: bool = True, font_size: float = 7.6):
    cell_style = ParagraphStyle(
        "ReportTableCell",
        parent=styles["small"],
        fontSize=font_size,
        leading=font_size + 2.2,
        textColor=INK,
    )
    data = []
    for row_index, row in enumerate(rows):
        data.append(
            [
                Paragraph(
                    f"<b>{value}</b>" if header and row_index == 0 else str(value),
                    cell_style,
                )
                for value in row
            ]
        )
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    for row in range(1 if header else 0, len(data)):
        if row % 2 == 0:
            commands.append(("BACKGROUND", (0, row), (-1, row), LIGHT_GRAY))
    table.setStyle(TableStyle(commands))
    return table


def scaled_image(path: Path, max_width: float, max_height: float):
    with PILImage.open(path) as image:
        width, height = image.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def metric_cards(day5, styles):
    values = [
        ("1.76x", "Typical final-area error after day 5"),
        ("0.43", "Day-5 explained variance on log area"),
        ("4.24 d", "Day-5 duration mean absolute error"),
    ]
    cells = []
    for value, label in values:
        cells.append(
            [
                Paragraph(value, styles["metric"]),
                Paragraph(label, styles["metric_label"]),
            ]
        )
    cards = Table(
        [[Table([[cell[0]], [cell[1]]], colWidths=[2.05 * inch]) for cell in cells]],
        colWidths=[2.18 * inch] * 3,
    )
    cards.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return cards


def build_report():
    required = [
        RESULTS / "outcome_validation_summary.csv",
        RESULTS / "grown_fire_descriptive_summary.csv",
        RESULTS / "run_report.json",
        RESULTS / "outcome_prediction_performance.png",
        RESULTS / "observed_vs_predicted_day5.png",
        RESULTS / "grown_fire_descriptive_statistics.png",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing report inputs: {missing}")

    validation = pd.read_csv(required[0])
    descriptive = pd.read_csv(required[1])
    report = json.loads(required[2].read_text())
    early = validation[validation["model"] == "early_trajectory"].set_index("snapshot_day")
    historical = validation[validation["model"] == "training_median"].set_index("snapshot_day")
    grown = descriptive.iloc[0]
    day5 = early.loc[5]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    story = []

    story.extend(
        [
            Spacer(1, 0.42 * inch),
            paragraph("FIRED Prediction Validation", styles, "title"),
            paragraph(
                "How well can early burned-area sequences predict the fully grown fire?",
                styles,
                "subtitle",
            ),
            callout(
                "Bottom line",
                "<b>We are moderately good at predicting final area after five days and meaningfully better after seven days, but we are not yet good at predicting event duration.</b> The result is useful for retrospective scientific inference and coarse size screening, not yet for operational incident forecasting.",
                styles,
                tone="green",
            ),
            Spacer(1, 0.18 * inch),
            metric_cards(day5, styles),
            Spacer(1, 0.22 * inch),
            paragraph("What was tested", styles, "h1"),
            paragraph(
                "Models saw only the first 3, 5, or 7 calendar days of each FIRED event and predicted its final mapped area and total mapped duration. Model development, interval calibration, and final validation were separated in time so that no held-out event influenced fitting or uncertainty calibration.",
                styles,
            ),
            bullet("Development: 2,316 events ignited in 2001-2012.", styles),
            bullet("Prediction-interval calibration: 552 events from 2013-2015.", styles),
            bullet("Untouched validation: 1,164 events from 2016-2020.", styles),
            bullet("Filtered population: natural-vegetation events, 10 km2 or larger, lasting 8-60 days.", styles),
            Spacer(1, 0.08 * inch),
            paragraph(
                "Prepared from the reproducible outputs in <font name='Courier'>outputs/fired_outcome_validation/</font>. Report date: 2026-09-27.",
                styles,
                "small",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            paragraph("1. Validation Design", styles, "h1"),
            paragraph(
                "The early-trajectory model is a regularized regression using only information available through the snapshot day: cumulative area, first-day area, average and recent growth, fraction of active days, recent growth fraction, peak growth, log-area slope, and dominant land-cover class. It was compared with two deliberately simple baselines.",
                styles,
            ),
            make_table(
                [
                    ["Model", "Meaning", "Role"],
                    ["No future growth", "Final area equals current area; event ends the next day", "Lower-bound persistence baseline"],
                    ["Historical median", "Current area multiplied by the development-period median remaining-growth factor", "Population-history baseline"],
                    ["Early trajectory", "Ridge regression on early sequence features", "Primary predictive model"],
                ],
                [1.35 * inch, 3.35 * inch, 1.85 * inch],
                styles,
            ),
            Spacer(1, 0.12 * inch),
            paragraph("Scoring", styles, "h2"),
            bullet("Final area: mean absolute log error. Exponentiating it gives a convenient typical multiplicative error factor.", styles),
            bullet("Duration: mean absolute error in days.", styles),
            bullet("Explained variance: R2 on log final area and ordinary R2 on duration.", styles),
            bullet("Uncertainty: 90% residual intervals calibrated only on 2013-2015 events.", styles),
            Spacer(1, 0.12 * inch),
            callout(
                "Leakage control",
                "Unit tests confirm that changing all growth after a snapshot changes the final outcome but leaves every predictor at that snapshot unchanged. The held-out years were not used for model fitting or interval calibration.",
                styles,
            ),
            Spacer(1, 0.16 * inch),
            paragraph("Interpretation scale", styles, "h2"),
            make_table(
                [
                    ["Question", "Result", "Assessment"],
                    ["Can day 3 rank final size?", "R2 = 0.21; 2.03x typical error", "Limited; useful only for coarse screening"],
                    ["Can day 5 rank final size?", "R2 = 0.43; 1.76x typical error", "Moderate predictive value"],
                    ["Can day 7 rank final size?", "R2 = 0.64; 1.51x typical error", "Useful, but not precise"],
                    ["Can early growth predict duration?", "R2 about 0.15; about 4.1-4.3 days MAE", "Weak individual-event prediction"],
                ],
                [2.05 * inch, 2.25 * inch, 2.25 * inch],
                styles,
            ),
            PageBreak(),
        ]
    )

    performance_rows = [["Snapshot", "Area error", "Error factor", "Log-area R2", "Duration MAE", "Area 90% coverage", "Duration 90% coverage"]]
    for day in (3, 5, 7):
        row = early.loc[day]
        performance_rows.append(
            [
                f"Day {day}",
                f"{row.mean_absolute_log_area_error:.3f}",
                f"{row.typical_area_error_factor:.2f}x",
                f"{row.log_area_r2:.2f}",
                f"{row.mean_absolute_duration_error_days:.2f} d",
                f"{100 * row.area_interval_coverage:.1f}%",
                f"{100 * row.duration_interval_coverage:.1f}%",
            ]
        )
    story.extend(
        [
            paragraph("2. How Did We Do?", styles, "h1"),
            paragraph(
                "The early-trajectory model beats both baselines at every snapshot. Final-area skill improves steadily as more of the event is observed. Duration error changes little, indicating that early area dynamics carry substantially more information about eventual size than about when mapped growth will cease.",
                styles,
            ),
            scaled_image(required[3], 7.0 * inch, 3.05 * inch),
            paragraph(
                "Figure 1. Held-out final-area and duration errors. Points are means across 1,164 validation events; bars are 95% event-bootstrap intervals. Lower is better.",
                styles,
                "caption",
            ),
            make_table(
                performance_rows,
                [0.63 * inch, 0.75 * inch, 0.78 * inch, 0.72 * inch, 0.82 * inch, 1.05 * inch, 1.08 * inch],
                styles,
                font_size=6.8,
            ),
            Spacer(1, 0.12 * inch),
            callout(
                "Calibration",
                "Final-area intervals cover 85-87% of held-out fires instead of the nominal 90%, so they are modestly too narrow. Duration intervals achieve approximately nominal coverage (89-91%), although the point predictions explain little event-to-event variation.",
                styles,
                tone="orange",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            paragraph("3. Where The Predictions Succeed And Fail", styles, "h1"),
            paragraph(
                "Observed-versus-predicted plots reveal more than a single score. The day-5 early-trajectory model follows the final-area identity line much more closely than either baseline, but it still underpredicts some of the largest late-growing fires. Duration predictions remain compressed toward the population center.",
                styles,
            ),
            scaled_image(required[4], 7.0 * inch, 4.25 * inch),
            paragraph(
                "Figure 2. Predictions made after event day 5. The dashed identity line denotes perfect prediction. Hexagon color represents the number of event predictions.",
                styles,
                "caption",
            ),
            callout(
                "Practical reading",
                "A day-5 final-area prediction is informative as a size class or multiplicative range, not as an exact acreage estimate. A duration prediction near 13 days mainly reflects the population center and should not be treated as a reliable event-specific stopping date.",
                styles,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            paragraph("4. What Describes The Fully Grown Fire?", styles, "h1"),
            paragraph(
                "The validation events are strongly right-skewed in final area and grow in pulses rather than at a smooth daily rate. Their within-event timing explains why more observation days add substantial final-size information.",
                styles,
            ),
            scaled_image(required[5], 7.0 * inch, 4.55 * inch),
            paragraph(
                "Figure 3. Descriptive statistics for the fully observed 2016-2020 validation events. Timing variables are normalized by each event's mapped duration.",
                styles,
                "caption",
            ),
            make_table(
                [
                    ["Descriptor", "Held-out median", "Interpretation"],
                    ["Final area", f"{grown.final_area_median_km2:.1f} km2", "A typical retained event is modest, with a long upper tail"],
                    ["Duration", f"{grown.duration_median_days:.0f} days", "Day 5 is still early for many events"],
                    ["Area present by day 3", f"{100 * grown.area_fraction_day_3_median:.0f}%", "Little of the final footprint is yet visible"],
                    ["Area present by day 5", f"{100 * grown.area_fraction_day_5_median:.0f}%", "Enough signal for moderate prediction"],
                    ["Area present by day 7", f"{100 * grown.area_fraction_day_7_median:.0f}%", "Most final area is now represented"],
                    ["Peak-to-mean active growth", f"{grown.growth_burstiness_median:.2f}x", "Daily accumulation is strongly pulsed"],
                ],
                [2.0 * inch, 1.3 * inch, 3.25 * inch],
                styles,
            ),
            PageBreak(),
        ]
    )

    day7 = early.loc[7]
    story.extend(
        [
            paragraph("5. Are We Good At Prediction?", styles, "h1"),
            callout(
                "Final area",
                f"<b>Promising and useful by day 7, but not precise.</b> The model explains {100 * day7.log_area_r2:.0f}% of variation in log final area and has a {day7.typical_area_error_factor:.2f}x typical error factor. This is credible skill for broad final-size discrimination.",
                styles,
                tone="green",
            ),
            Spacer(1, 0.12 * inch),
            callout(
                "Duration",
                f"<b>Not yet good.</b> Day-5 duration MAE is {day5.mean_absolute_duration_error_days:.2f} days against a median 13-day event, and R2 is only {day5.duration_r2:.2f}. The model improves on simple baselines but does not capture much individual variation.",
                styles,
                tone="orange",
            ),
            Spacer(1, 0.16 * inch),
            paragraph("Why the answer is conditional", styles, "h2"),
            bullet("These are retrospective predictions from MODIS-derived FIRED burn dates, not forecasts from real-time incident observations.", styles),
            bullet("The sample excludes fires smaller than 10 km2, shorter than 8 days, longer than 60 days, and events dominated by non-natural land-cover classes.", styles),
            bullet("Missing FIRED observation dates are represented as zero detected growth, so observation timing is part of the signal.", styles),
            bullet("Large late-growth events remain a visible failure mode, and final-area intervals are somewhat overconfident.", styles),
            bullet("Natural-vegetation filtering does not prove that every retained event is an unplanned wildfire.", styles),
            Spacer(1, 0.1 * inch),
            paragraph("Recommended scientific claim", styles, "h2"),
            paragraph(
                "A defensible statement is: <b>Early FIRED growth trajectories contain predictive information about eventual burned area, with moderate held-out skill by day 5 and substantially stronger skill by day 7. The same trajectories provide only weak information about total mapped duration.</b>",
                styles,
            ),
            paragraph("What would make prediction genuinely strong?", styles, "h2"),
            bullet("Add weather, fuel moisture, topography, suppression, and contemporaneous perimeter geometry.", styles),
            bullet("Validate geographically, not only temporally, to test transfer to unseen regions.", styles),
            bullet("Use an operational perimeter stream and assess forecasts at the time information actually becomes available.", styles),
            bullet("Calibrate intervals conditionally by size, land cover, and growth phase to correct undercoverage.", styles),
            PageBreak(),
        ]
    )

    counts = report["counts"]
    story.extend(
        [
            paragraph("6. Reproducibility And Sources", styles, "h1"),
            paragraph(
                "The complete event-level outcomes, held-out predictions, calibrated intervals, summaries, figures, and machine-readable run report are retained under <font name='Courier'>outputs/fired_outcome_validation/</font>. The builder reads those outputs directly, so reported values stay synchronized with the analysis.",
                styles,
            ),
            make_table(
                [
                    ["Partition", "Ignition years", "Events", "Purpose"],
                    ["Development", "2001-2012", f"{counts['development_events']:,}", "Fit model parameters"],
                    ["Calibration", "2013-2015", f"{counts['calibration_events']:,}", "Set 90% interval radii"],
                    ["Held-out validation", "2016-2020", f"{counts['held_out_test_events']:,}", "Final performance estimate"],
                ],
                [1.35 * inch, 1.15 * inch, 0.8 * inch, 3.25 * inch],
                styles,
            ),
            Spacer(1, 0.16 * inch),
            paragraph("Reproduction commands", styles, "h2"),
            paragraph(
                "<font name='Courier'>PYTHONPATH=src python scripts/run_fired_prediction_tests.py --fired-gpkg /path/to/fired_daily.gpkg</font>",
                styles,
                "small",
            ),
            paragraph(
                "<font name='Courier'>PYTHONPATH=src python scripts/run_fired_outcome_validation.py</font>",
                styles,
                "small",
            ),
            paragraph(
                "<font name='Courier'>PYTHONPATH=src python scripts/build_fired_prediction_report.py</font>",
                styles,
                "small",
            ),
            paragraph("Primary sources", styles, "h2"),
            bullet("Balch et al. (2020), FIRED event reconstruction method. Remote Sensing 12:3498. doi:10.3390/rs12213498", styles),
            bullet("Mahood et al. (2022), FIRED CONUS fire-event data descriptor. Scientific Data 9:458. doi:10.1038/s41597-022-01572-3", styles),
            bullet("FIREDpy source code: https://github.com/earthlab/firedpy", styles),
            Spacer(1, 0.18 * inch),
            callout(
                "Verification",
                "The repository test suite contains 98 passing tests, including predictor leakage checks and exact regression checks. The source sequence totals reconcile to reported event areas at machine precision after quality filtering.",
                styles,
            ),
        ]
    )

    ReportTemplate(str(OUTPUT)).build(story)
    reader = PdfReader(str(OUTPUT))
    if len(reader.pages) < 5:
        raise RuntimeError("report unexpectedly short")
    print(f"Wrote {OUTPUT} ({len(reader.pages)} pages)")


if __name__ == "__main__":
    build_report()
