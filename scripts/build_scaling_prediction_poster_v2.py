#!/usr/bin/env python3
"""Build a second poster around origin-anchored scaling and prediction."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import build_results_poster as base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "output" / "pdf" / "fire_scaling_prediction_poster_v2.pdf"
)
PAGE_SIZE = landscape((24 * 72, 36 * 72))

BG = HexColor("#FFFFFF")
INK = HexColor("#202428")
MUTED = HexColor("#687078")
GRID = HexColor("#D9DEE2")
BLUE = HexColor("#4F86DF")
BLUE_DARK = HexColor("#245DA8")
BLUE_PALE = HexColor("#E8F0FB")
RED = HexColor("#C52F2A")
RED_DARK = HexColor("#92211F")
RED_PALE = HexColor("#F7E6E3")
TEAL = HexColor("#16776D")
TEAL_PALE = HexColor("#E4F1EF")
GOLD = HexColor("#E2B23A")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=ROOT / "tmp" / "pdfs" / "scaling_prediction_poster_v2",
    )
    return parser.parse_args()


def interpolate_color(low: Color, high: Color, value: float) -> Color:
    value = max(0.0, min(1.0, value))
    return Color(
        low.red + value * (high.red - low.red),
        low.green + value * (high.green - low.green),
        low.blue + value * (high.blue - low.blue),
    )


def draw_origin_density(
    pdf: canvas.Canvas,
    x_values: np.ndarray,
    y_values: np.ndarray,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    weights: np.ndarray | None,
    title: str,
    sample_label: str,
    primary_slope: float,
    primary_color: Color,
    primary_label: str,
    secondary_slope: float,
    secondary_color: Color,
    secondary_label: str,
) -> float:
    fitted_slope, raw_intercept = base._weighted_fit(x_values, y_values, weights)
    x_anchor = float(np.min(x_values))
    y_anchor = raw_intercept + fitted_slope * x_anchor
    x_relative = x_values - x_anchor
    y_relative = y_values - y_anchor
    fitted_slope, fitted_intercept = base._weighted_fit(
        x_relative, y_relative, weights
    )
    if abs(fitted_intercept) > 1e-10:
        raise AssertionError("Centered regression did not produce a zero intercept")

    plot_left = x + 72
    plot_right = x + width - 20
    plot_bottom = y + 66
    plot_top = y + height - 55
    x_low = 0.0
    x_high = float(np.ceil(np.percentile(x_relative, 99.8) * 2) / 2)
    y_low = 0.0
    y_high = float(
        np.ceil(
            max(
                np.percentile(y_relative, 99.8),
                primary_slope * x_high,
                secondary_slope * x_high,
            )
            * 2
        )
        / 2
    )

    def sx(value: float) -> float:
        return plot_left + (value - x_low) / (x_high - x_low) * (
            plot_right - plot_left
        )

    def sy(value: float) -> float:
        return plot_bottom + (value - y_low) / (y_high - y_low) * (
            plot_top - plot_bottom
        )

    pdf.setFillColor(Color(1, 1, 1))
    pdf.rect(x, y, width, height, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 19)
    pdf.drawString(x + 16, y + height - 29, title)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10.5)
    pdf.drawRightString(x + width - 18, y + height - 28, sample_label)

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(0.7)
    for tick in np.arange(0.0, x_high + 0.01, 0.5):
        pdf.line(sx(float(tick)), plot_bottom, sx(float(tick)), plot_top)
    for tick in np.arange(0.0, y_high + 0.01, 0.5):
        pdf.line(plot_left, sy(float(tick)), plot_right, sy(float(tick)))

    counts, x_edges, y_edges = np.histogram2d(
        x_relative,
        y_relative,
        bins=(56, 48),
        range=((x_low, x_high), (y_low, y_high)),
    )
    maximum = float(np.log1p(counts.max()))
    pale = BLUE_PALE if primary_color == BLUE else RED_PALE
    dark = BLUE_DARK if primary_color == BLUE else RED_DARK
    for x_index in range(counts.shape[0]):
        for y_index in range(counts.shape[1]):
            count = counts[x_index, y_index]
            if count <= 0:
                continue
            intensity = float(np.log1p(count) / maximum)
            pdf.setFillColor(interpolate_color(pale, dark, intensity))
            left = sx(float(x_edges[x_index]))
            right = sx(float(x_edges[x_index + 1]))
            bottom = sy(float(y_edges[y_index]))
            top = sy(float(y_edges[y_index + 1]))
            pdf.rect(
                left,
                bottom,
                right - left + 0.3,
                top - bottom + 0.3,
                fill=1,
                stroke=0,
            )

    def relation(slope: float, color: Color, dash: list[int], line_width: float):
        pdf.setStrokeColor(color)
        pdf.setLineWidth(line_width)
        pdf.setDash(dash)
        pdf.line(sx(x_low), sy(slope * x_low), sx(x_high), sy(slope * x_high))
        pdf.setDash([])

    relation(secondary_slope, secondary_color, [10, 7], 3.0)
    relation(primary_slope, primary_color, [], 4.8)
    relation(fitted_slope, INK, [2, 5], 2.8)

    pdf.setFillColor(INK)
    pdf.circle(sx(0), sy(0), 5, fill=1, stroke=0)
    pdf.setStrokeColor(INK)
    pdf.setLineWidth(1.2)
    pdf.rect(
        plot_left,
        plot_bottom,
        plot_right - plot_left,
        plot_top - plot_bottom,
        fill=0,
        stroke=1,
    )
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 10.5)
    for tick in np.arange(0.0, x_high + 0.01, 0.5):
        pdf.drawCentredString(sx(float(tick)), plot_bottom - 18, f"{tick:g}")
    for tick in np.arange(0.0, y_high + 0.01, 0.5):
        pdf.drawRightString(plot_left - 9, sy(float(tick)) - 4, f"{tick:g}")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(
        (plot_left + plot_right) / 2,
        y + 22,
        "Relative log10 area  log10(A / A0)",
    )
    pdf.saveState()
    pdf.translate(x + 18, (plot_bottom + plot_top) / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, "Relative log10 perimeter  log10(P / P0)")
    pdf.restoreState()

    legend_x = plot_left + 14
    legend_y = plot_top - 18
    pdf.setFillColor(Color(1, 1, 1, alpha=0.90))
    pdf.rect(legend_x - 8, legend_y - 64, 252, 79, fill=1, stroke=0)
    legend = [
        (primary_color, [], primary_label),
        (secondary_color, [9, 6], secondary_label),
        (INK, [2, 4], f"regression: {fitted_slope:.3f}"),
    ]
    for index, (color, dash, label) in enumerate(legend):
        row_y = legend_y - index * 22
        pdf.setStrokeColor(color)
        pdf.setLineWidth(3.2)
        pdf.setDash(dash)
        pdf.line(legend_x, row_y, legend_x + 38, row_y)
        pdf.setDash([])
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", 10.5)
        pdf.drawString(legend_x + 47, row_y - 4, label)
    return fitted_slope


def prepare_images(work_dir: Path) -> dict[str, Path]:
    concept = (
        ROOT
        / "outputs"
        / "conceptual_detection_prediction"
        / "figure_detection_prediction_concept.png"
    )
    prediction = ROOT / "output" / "manuscript" / "figure_prediction.png"
    missing = [str(path) for path in (concept, prediction) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing poster sources: " + ", ".join(missing))
    work_dir.mkdir(parents=True, exist_ok=True)
    concept_crop = base.crop_fraction(
        concept, work_dir / "concept_no_title.png", (0.0, 0.085, 1.0, 1.0)
    )
    forecast_crop = base.crop_fraction(
        prediction, work_dir / "forecast.png", (0.012, 0.055, 0.500, 0.505)
    )
    base.erase_fraction(forecast_crop, (0.000, 0.000, 0.055, 0.075))
    return {"concept": concept_crop, "forecast": forecast_crop}


def draw_metric(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    value: str,
    headline: str,
    detail: str,
    color: Color,
) -> None:
    pdf.setFillColor(color)
    pdf.rect(x, y + 112, width, 5, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 27)
    pdf.drawString(x + 22, y + 70, value)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 12.5)
    pdf.drawString(x + 22, y + 43, headline)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10.5)
    pdf.drawString(x + 22, y + 20, detail)


def build_poster(output: Path, work_dir: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    images = prepare_images(work_dir)
    fired_x, fired_y, fired_weights = base.load_fired_between_geometry()
    model_x, model_y = base.load_model_geometry()

    page_width, page_height = PAGE_SIZE
    pdf = canvas.Canvas(str(output), pagesize=PAGE_SIZE, pageCompression=1)
    pdf.setTitle("From fireline spread to geometric state and prediction")
    pdf.setAuthor("spread-vs-growth")
    pdf.setSubject("Origin-anchored scaling regressions and held-out FIRED prediction")
    pdf.setFillColor(BG)
    pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    margin = 56
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 52)
    pdf.drawString(
        margin,
        page_height - 86,
        "The fireline predicts one-half. Real fires organize near two-thirds.",
    )
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 21)
    pdf.drawString(
        margin,
        page_height - 122,
        "Origin-anchored regressions isolate the exponent; mapped geometry then constrains near-term prediction.",
    )
    pdf.setFillColor(RED)
    pdf.rect(margin, page_height - 149, page_width - 2 * margin, 5, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawRightString(
        page_width - margin,
        page_height - 92,
        "SPREAD VS GROWTH  |  FIRE METABOLISM",
    )

    left_x = margin
    left_width = 1510
    right_x = left_x + left_width + 44
    right_width = page_width - margin - right_x
    section_top = page_height - 194

    pdf.setFillColor(RED)
    pdf.circle(left_x + 15, section_top, 15, fill=1, stroke=0)
    pdf.setFillColor(Color(1, 1, 1))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(left_x + 15, section_top - 6, "1")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(left_x + 43, section_top - 8, "The scaling gap")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 13.5)
    pdf.drawString(
        left_x + 43,
        section_top - 32,
        "Each cloud is normalized to a low-scale fitted anchor, so both reference laws and the regression begin at (0,0).",
    )

    plot_gap = 28
    plot_width = (left_width - plot_gap) / 2
    plot_y = 900
    plot_height = 575
    fired_slope = draw_origin_density(
        pdf,
        fired_x,
        fired_y,
        left_x,
        plot_y,
        plot_width,
        plot_height,
        weights=fired_weights,
        title="A  FIRED fire-level geometry",
        sample_label=f"{len(fired_x):,} fires",
        primary_slope=2.0 / 3.0,
        primary_color=BLUE,
        primary_label="two-thirds reference",
        secondary_slope=0.5,
        secondary_color=RED,
        secondary_label="one-half reference",
    )
    model_slope = draw_origin_density(
        pdf,
        model_x,
        model_y,
        left_x + plot_width + plot_gap,
        plot_y,
        plot_width,
        plot_height,
        weights=None,
        title="B  Smooth-front benchmarks",
        sample_label=f"{len(model_x):,} outputs",
        primary_slope=0.5,
        primary_color=RED,
        primary_label="one-half reference",
        secondary_slope=2.0 / 3.0,
        secondary_color=BLUE,
        secondary_label="two-thirds reference",
    )
    if abs(fired_slope - 0.6458843786) > 1e-6:
        raise AssertionError(f"Unexpected FIRED slope: {fired_slope}")
    if abs(model_slope - 0.506282956) > 1e-6:
        raise AssertionError(f"Unexpected model slope: {model_slope}")

    pdf.setStrokeColor(BLUE)
    pdf.setLineWidth(4)
    pdf.line(left_x, 866, left_x + plot_width, 866)
    pdf.setStrokeColor(RED)
    pdf.line(
        left_x + plot_width + plot_gap,
        866,
        left_x + 2 * plot_width + plot_gap,
        866,
    )
    pdf.setFillColor(BLUE_DARK)
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawString(left_x + 22, 810, "0.646")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(left_x + 143, 818, "observed between-fire slope")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(left_x + 143, 791, "95% CI 0.639-0.652; near 2/3, not 1/2")

    second_x = left_x + plot_width + plot_gap
    pdf.setFillColor(RED_DARK)
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawString(second_x + 22, 810, "0.506")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(second_x + 143, 818, "baseline model-cloud slope")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(second_x + 143, 791, "95% CI 0.505-0.507; near 1/2, not 2/3")

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(1)
    pdf.line(left_x, 712, left_x + left_width, 712)
    pdf.setStrokeColor(BLUE)
    pdf.setLineWidth(7)
    pdf.line(left_x + 35, 520, left_x + 355, 680)
    pdf.setStrokeColor(RED)
    pdf.setLineWidth(7)
    pdf.line(left_x + 35, 520, left_x + 355, 640)
    pdf.setFillColor(BLUE_DARK)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(left_x + 375, 666, "organized population geometry: 2/3")
    pdf.setFillColor(RED_DARK)
    pdf.drawString(left_x + 375, 626, "local smooth-front geometry: 1/2")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(left_x + 760, 658, "Same origin. Different scaling law.")
    base.draw_wrapped(
        pdf,
        "The relative axes remove the dimensional coefficient from the visual comparison. Black dotted regressions are estimated from data; colored reference laws share the same low-scale origin. This tests slopes without claiming that perimeter has coefficient one in raw kilometers.",
        left_x + 760,
        622,
        left_width - 790,
        size=14,
        leading=19,
        color=MUTED,
    )

    pdf.setStrokeColor(GRID)
    pdf.line(left_x, 444, left_x + left_width, 444)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(left_x + 24, 400, "What changes for fire prediction")
    implications = [
        "Whole-fire growth is not exhausted by local fireline propagation.",
        "Mapped perimeter, topology, and boundary change record the current state.",
        "Geometry improves held-out forecasts when combined with area and recent dynamics.",
    ]
    implication_y = 360
    for statement in implications:
        pdf.setFillColor(TEAL)
        pdf.circle(left_x + 32, implication_y + 4, 4.5, fill=1, stroke=0)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", 14)
        pdf.drawString(left_x + 48, implication_y, statement)
        implication_y -= 43

    pdf.setFillColor(TEAL)
    pdf.circle(right_x + 15, section_top, 15, fill=1, stroke=0)
    pdf.setFillColor(Color(1, 1, 1))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(right_x + 15, section_top - 6, "2")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(right_x + 43, section_top - 8, "Geometry becomes state")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 13.5)
    pdf.drawString(
        right_x + 43,
        section_top - 32,
        "Read backward to detect change; propagate forward to narrow futures.",
    )
    base.draw_image_contain(
        pdf, images["concept"], right_x, 815, right_width, 650, pad=3
    )

    pdf.setFillColor(TEAL)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(right_x + 8, 770, "Held-out FIRED prediction")
    base.draw_image_contain(
        pdf, images["forecast"], right_x, 398, right_width, 350, pad=3
    )
    draw_metric(
        pdf,
        right_x,
        248,
        (right_width - 18) / 2,
        "13.3%",
        "lower seven-day error",
        "geometry proxy vs area dynamics",
        TEAL,
    )
    draw_metric(
        pdf,
        right_x + (right_width - 18) / 2 + 18,
        248,
        (right_width - 18) / 2,
        "0.790",
        "future acceleration",
        "held-out balanced accuracy",
        GOLD,
    )

    pdf.setFillColor(TEAL)
    pdf.rect(margin, 202, page_width - 2 * margin, 5, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(margin + 20, 164, "Evidence boundary")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 12.5)
    pdf.drawString(
        margin + 20,
        134,
        "Observed population scaling and held-out predictive gains are empirical. The residual detects change, not its cause; fuel, weather, barriers, and suppression require independent data.",
    )
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        margin + 20,
        104,
        "FIRED cohort: 4,032 fires. Model cloud: exact ellipses, Huygens wavelets, and cellular-neighbor benchmarks; amplified heterogeneous fronts are treated separately.",
    )
    pdf.drawRightString(
        page_width - margin - 20,
        104,
        "github.com/CU-ESIIL/spread-vs-growth",
    )

    pdf.showPage()
    pdf.save()
    return output


def main() -> None:
    args = parse_args()
    build_poster(args.output.resolve(), args.work_dir.resolve())


if __name__ == "__main__":
    main()
