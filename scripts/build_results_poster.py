#!/usr/bin/env python3
"""Build a publication-ready poster from locked repository results."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import wrap

import numpy as np
import pandas as pd
from PIL import Image
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "fire_geometry_state_prediction_poster.pdf"
PAGE_SIZE = landscape((24 * 72, 36 * 72))

BG = HexColor("#FBFAF7")
INK = HexColor("#202428")
MUTED = HexColor("#687078")
GRID = HexColor("#D8DDE1")
FIRE = HexColor("#B92B26")
FIRE_DARK = HexColor("#8F1F25")
FIRE_PALE = HexColor("#F4E4E1")
BLUE = HexColor("#6495ED")
BLUE_DARK = HexColor("#3467A8")
BLUE_PALE = HexColor("#EAF1FA")
TEAL = HexColor("#176F65")
TEAL_PALE = HexColor("#E2F0ED")
GOLD = HexColor("#E6B84A")

FIRED_SEQUENCES = ROOT / "outputs" / "fired_prediction" / "fired_sequences.csv.gz"
FIRED_GEOMETRY = (
    ROOT
    / "outputs"
    / "fired_lifecycle_prediction"
    / "fired_geometry_sequences.csv.gz"
)
MODEL_RUNS = (
    ROOT
    / "outputs"
    / "datasets"
    / "model_hexbin_handoff"
    / "model_runs_other_models.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--work-dir", type=Path, default=ROOT / "tmp" / "pdfs" / "results_poster"
    )
    return parser.parse_args()


def crop_fraction(
    source: Path,
    destination: Path,
    box: tuple[float, float, float, float],
) -> Path:
    with Image.open(source) as image:
        width, height = image.size
        pixels = (
            round(box[0] * width),
            round(box[1] * height),
            round(box[2] * width),
            round(box[3] * height),
        )
        cropped = image.crop(pixels)
        destination.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(destination, optimize=True)
    return destination


def erase_fraction(
    image_path: Path, box: tuple[float, float, float, float]
) -> Path:
    with Image.open(image_path) as image:
        cleaned = image.convert("RGB")
        width, height = cleaned.size
        pixels = (
            round(box[0] * width),
            round(box[1] * height),
            round(box[2] * width),
            round(box[3] * height),
        )
        cleaned.paste((255, 255, 255), pixels)
        cleaned.save(image_path, optimize=True)
    return image_path


def draw_image_contain(
    pdf: canvas.Canvas,
    image_path: Path,
    x: float,
    y: float,
    width: float,
    height: float,
    pad: float = 0,
) -> None:
    with Image.open(image_path) as image:
        image_width, image_height = image.size
    scale = min(
        (width - 2 * pad) / image_width,
        (height - 2 * pad) / image_height,
    )
    draw_width = image_width * scale
    draw_height = image_height * scale
    draw_x = x + (width - draw_width) / 2
    draw_y = y + (height - draw_height) / 2
    pdf.drawImage(
        ImageReader(str(image_path)),
        draw_x,
        draw_y,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        mask="auto",
    )


def _weighted_fit(
    x: np.ndarray, y: np.ndarray, weights: np.ndarray | None = None
) -> tuple[float, float]:
    if weights is None:
        weights = np.ones_like(x)
    total = float(weights.sum())
    x_mean = float(np.dot(weights, x) / total)
    y_mean = float(np.dot(weights, y) / total)
    slope = float(
        np.dot(weights, (x - x_mean) * (y - y_mean))
        / np.dot(weights, (x - x_mean) ** 2)
    )
    return slope, y_mean - slope * x_mean


def load_fired_between_geometry() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sequences = pd.read_csv(
        FIRED_SEQUENCES,
        usecols=["id", "event_day", "daily_area_km2", "cumulative_area_km2"],
    )
    geometry = pd.read_csv(
        FIRED_GEOMETRY,
        usecols=["id", "event_day", "exterior_perimeter_km"],
    )
    panel = sequences.merge(
        geometry, on=["id", "event_day"], how="inner", validate="one_to_one"
    )
    panel = panel[
        (panel.daily_area_km2 > 0)
        & (panel.cumulative_area_km2 > 0)
        & (panel.exterior_perimeter_km > 0)
    ].copy()
    panel["log_area"] = np.log10(panel.cumulative_area_km2)
    panel["log_perimeter"] = np.log10(panel.exterior_perimeter_km)
    events = panel.groupby("id", sort=False).agg(
        log_area=("log_area", "mean"),
        log_perimeter=("log_perimeter", "mean"),
        observations=("id", "size"),
    )
    return (
        events.log_area.to_numpy(dtype=float),
        events.log_perimeter.to_numpy(dtype=float),
        events.observations.to_numpy(dtype=float),
    )


def load_model_geometry() -> tuple[np.ndarray, np.ndarray]:
    frame = pd.read_csv(
        MODEL_RUNS,
        usecols=[
            "area_km2",
            "exterior_perimeter_km",
            "valid_geometry",
            "include_in_plot",
        ],
    )
    frame = frame[
        frame.valid_geometry.astype(bool)
        & frame.include_in_plot.astype(bool)
        & (frame.area_km2 > 0)
        & (frame.exterior_perimeter_km > 0)
    ]
    return (
        np.log10(frame.area_km2.to_numpy(dtype=float)),
        np.log10(frame.exterior_perimeter_km.to_numpy(dtype=float)),
    )


def _density_color(value: float) -> Color:
    stops = (
        (0.00, (1.00, 0.97, 0.68)),
        (0.36, (0.98, 0.40, 0.34)),
        (0.68, (0.48, 0.10, 0.48)),
        (1.00, (0.04, 0.03, 0.12)),
    )
    value = max(0.0, min(1.0, value))
    for (lower, rgb_lower), (upper, rgb_upper) in zip(stops[:-1], stops[1:]):
        if value <= upper:
            fraction = (value - lower) / (upper - lower)
            rgb = tuple(
                left + fraction * (right - left)
                for left, right in zip(rgb_lower, rgb_upper)
            )
            return Color(*rgb)
    return Color(*stops[-1][1])


def _tick_label(exponent: int) -> str:
    if exponent < 0:
        return f"{10**exponent:g}"
    return f"{10**exponent:d}"


def draw_log_density_plot(
    pdf: canvas.Canvas,
    x_values: np.ndarray,
    y_values: np.ndarray,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fit_weights: np.ndarray | None,
    sample_label: str,
    blue_label: str,
) -> tuple[float, float]:
    """Draw a vector log-log density plot with an origin-fixed half line."""
    fit_slope, fit_intercept = _weighted_fit(x_values, y_values, fit_weights)
    if fit_weights is None:
        x_center = float(np.mean(x_values))
        y_center = float(np.mean(y_values))
    else:
        x_center = float(np.average(x_values, weights=fit_weights))
        y_center = float(np.average(y_values, weights=fit_weights))
    two_thirds_intercept = y_center - (2.0 / 3.0) * x_center

    plot_left = x + 67
    plot_right = x + width - 15
    plot_bottom = y + 52
    plot_top = y + height - 20
    x_low = np.floor(np.percentile(x_values, 0.4) * 2) / 2
    x_high = np.ceil(np.percentile(x_values, 99.6) * 2) / 2
    candidate_low = min(
        float(np.percentile(y_values, 0.4)),
        0.5 * x_low,
        fit_intercept + fit_slope * x_low,
        two_thirds_intercept + (2.0 / 3.0) * x_low,
    )
    candidate_high = max(
        float(np.percentile(y_values, 99.6)),
        0.5 * x_high,
        fit_intercept + fit_slope * x_high,
        two_thirds_intercept + (2.0 / 3.0) * x_high,
    )
    y_low = np.floor(candidate_low * 2) / 2
    y_high = np.ceil(candidate_high * 2) / 2

    def scale_x(value: float) -> float:
        return plot_left + (value - x_low) / (x_high - x_low) * (plot_right - plot_left)

    def scale_y(value: float) -> float:
        return plot_bottom + (value - y_low) / (y_high - y_low) * (plot_top - plot_bottom)

    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.rect(x, y, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(0.7)
    for tick in range(int(np.ceil(x_low)), int(np.floor(x_high)) + 1):
        pdf.line(scale_x(tick), plot_bottom, scale_x(tick), plot_top)
    for tick in range(int(np.ceil(y_low)), int(np.floor(y_high)) + 1):
        pdf.line(plot_left, scale_y(tick), plot_right, scale_y(tick))

    counts, x_edges, y_edges = np.histogram2d(
        x_values,
        y_values,
        bins=(52, 44),
        range=((x_low, x_high), (y_low, y_high)),
    )
    maximum = float(np.log1p(counts.max()))
    for x_index in range(counts.shape[0]):
        for y_index in range(counts.shape[1]):
            count = counts[x_index, y_index]
            if count <= 0:
                continue
            intensity = float(np.log1p(count) / maximum)
            pdf.setFillColor(_density_color(intensity))
            left = scale_x(float(x_edges[x_index]))
            right = scale_x(float(x_edges[x_index + 1]))
            bottom = scale_y(float(y_edges[y_index]))
            top = scale_y(float(y_edges[y_index + 1]))
            pdf.rect(left, bottom, right - left + 0.25, top - bottom + 0.25, fill=1, stroke=0)

    def draw_relation(slope: float, intercept: float, color, dash=None, width_value=3.5):
        pdf.setStrokeColor(color)
        pdf.setLineWidth(width_value)
        pdf.setDash(dash or [])
        samples = np.linspace(x_low, x_high, 240)
        previous: tuple[float, float] | None = None
        for x_value in samples:
            y_value = intercept + slope * x_value
            current = (scale_x(float(x_value)), scale_y(float(y_value)))
            if y_low <= y_value <= y_high:
                if previous is not None:
                    pdf.line(previous[0], previous[1], current[0], current[1])
                previous = current
            else:
                previous = None
        pdf.setDash([])

    draw_relation(0.5, 0.0, FIRE, [11, 7], 4.2)
    draw_relation(2.0 / 3.0, two_thirds_intercept, BLUE, None, 4.2)
    draw_relation(fit_slope, fit_intercept, INK, [2, 5], 2.8)

    pdf.setStrokeColor(INK)
    pdf.setLineWidth(1.2)
    pdf.rect(plot_left, plot_bottom, plot_right - plot_left, plot_top - plot_bottom, fill=0, stroke=1)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 10.5)
    for tick in range(int(np.ceil(x_low)), int(np.floor(x_high)) + 1):
        pdf.drawCentredString(scale_x(tick), plot_bottom - 17, _tick_label(tick))
    for tick in range(int(np.ceil(y_low)), int(np.floor(y_high)) + 1):
        pdf.drawRightString(plot_left - 8, scale_y(tick) - 4, _tick_label(tick))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString((plot_left + plot_right) / 2, y + 11, "Area (km2, log scale)")
    pdf.saveState()
    pdf.translate(x + 14, (plot_bottom + plot_top) / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, "Perimeter (km, log scale)")
    pdf.restoreState()

    legend_x = plot_left + 13
    legend_y = plot_top - 18
    pdf.setFillColor(Color(1, 1, 1, alpha=0.88))
    pdf.rect(legend_x - 8, legend_y - 62, 250, 77, fill=1, stroke=0)
    legend = [
        (BLUE, None, blue_label),
        (FIRE, [9, 5], "P = A^(1/2), intercept = 0"),
        (INK, [2, 4], f"fitted slope = {fit_slope:.3f}"),
    ]
    for index, (color, dash, label) in enumerate(legend):
        row_y = legend_y - index * 22
        pdf.setStrokeColor(color)
        pdf.setLineWidth(3)
        pdf.setDash(dash or [])
        pdf.line(legend_x, row_y, legend_x + 35, row_y)
        pdf.setDash([])
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", 10.5)
        pdf.drawString(legend_x + 44, row_y - 4, label)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(plot_right - 4, plot_bottom + 8, sample_label)
    return fit_slope, fit_intercept


def draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font: str = "Helvetica",
    size: float = 14,
    leading: float | None = None,
    color=INK,
    max_lines: int | None = None,
) -> float:
    leading = leading or size * 1.25
    average_char_width = size * 0.50
    line_chars = max(8, int(width / average_char_width))
    lines = wrap(text, line_chars, break_long_words=False)
    if max_lines is not None:
        lines = lines[:max_lines]
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def draw_section_heading(
    pdf: canvas.Canvas, label: str, title: str, x: float, y: float, color
) -> None:
    pdf.setFillColor(color)
    pdf.circle(x + 15, y + 3, 15, fill=1, stroke=0)
    pdf.setFillColor(BG)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(x + 15, y - 3, label)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 23)
    pdf.drawString(x + 43, y - 6, title)


def draw_metric(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    value: str,
    label: str,
    color,
) -> None:
    pdf.setFillColor(color)
    pdf.rect(x, y, 7, 125, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 31)
    pdf.drawString(x + 24, y + 74, value)
    draw_wrapped(
        pdf,
        label,
        x + 24,
        y + 48,
        width - 30,
        size=13,
        leading=16,
        color=MUTED,
        max_lines=2,
    )


def draw_estimand_comparison(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    pdf.setFillColor(HexColor("#F7F7F5"))
    pdf.rect(x, y, width, height, fill=1, stroke=0)
    plot_left = x + 148
    plot_right = x + width - 30
    plot_bottom = y + 48
    plot_top = y + height - 42

    def scale(value: float) -> float:
        return plot_left + (value - 0.48) / (0.77 - 0.48) * (plot_right - plot_left)

    references = [
        (0.5, FIRE, "1/2"),
        (2 / 3, BLUE, "2/3"),
        (0.75, HexColor("#2E8B57"), "3/4"),
    ]
    for value, color, label in references:
        location = scale(value)
        pdf.setStrokeColor(color)
        pdf.setLineWidth(2)
        pdf.line(location, plot_bottom, location, plot_top)
        pdf.setFillColor(color)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(location, plot_top + 10, label)

    rows = [
        ("Between fires", 0.645884, 0.639075, 0.651978, plot_top - 38),
        ("Within fires", 0.594068, 0.591687, 0.596546, plot_bottom + 28),
    ]
    for label, estimate, lower, upper, row_y in rows:
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawRightString(plot_left - 18, row_y - 5, label)
        pdf.setStrokeColor(INK)
        pdf.setLineWidth(3)
        pdf.line(scale(lower), row_y, scale(upper), row_y)
        pdf.setFillColor(INK)
        pdf.circle(scale(estimate), row_y, 7, fill=1, stroke=0)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(scale(upper) + 10, row_y - 4, f"{estimate:.3f}")

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(1)
    pdf.line(plot_left, plot_bottom - 8, plot_right, plot_bottom - 8)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 11)
    for tick in (0.5, 0.6, 0.7):
        pdf.drawCentredString(scale(tick), plot_bottom - 25, f"{tick:.1f}")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString((plot_left + plot_right) / 2, y + 8, "Exponent")


def draw_model_slope_comparison(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    pdf.setFillColor(HexColor("#F7F7F5"))
    pdf.rect(x, y, width, height, fill=1, stroke=0)
    plot_left = x + 185
    plot_right = x + width - 30
    plot_bottom = y + 42
    plot_top = y + height - 32

    def scale(value: float) -> float:
        return plot_left + (value - 0.45) / (0.70 - 0.45) * (plot_right - plot_left)

    for value, color, label in [(0.5, FIRE, "1/2"), (2 / 3, BLUE, "2/3")]:
        location = scale(value)
        pdf.setStrokeColor(color)
        pdf.setLineWidth(2)
        pdf.line(location, plot_bottom, location, plot_top)
        pdf.setFillColor(color)
        pdf.setFont("Helvetica-Bold", 10.5)
        pdf.drawCentredString(location, plot_top + 7, label)

    rows = [
        ("Pooled model cloud", 0.5063, 0.5055, 0.5071),
        ("Exact ellipse", 0.4999, 0.4959, 0.5038),
        ("Normal-front level set", 0.5003, 0.4995, 0.5011),
        ("Cellular neighbor", 0.4787, 0.4775, 0.4799),
        ("Huygens wavelets", 0.5481, 0.5470, 0.5492),
    ]
    row_step = (plot_top - plot_bottom - 8) / (len(rows) - 1)
    for index, (label, estimate, lower, upper) in enumerate(rows):
        row_y = plot_top - 6 - index * row_step
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold" if index == 0 else "Helvetica", 10.5)
        pdf.drawRightString(plot_left - 14, row_y - 4, label)
        pdf.setStrokeColor(INK)
        pdf.setLineWidth(2.2 if index == 0 else 1.7)
        pdf.line(scale(lower), row_y, scale(upper), row_y)
        pdf.setFillColor(TEAL if index == 0 else INK)
        pdf.circle(scale(estimate), row_y, 5.5 if index == 0 else 4.5, fill=1, stroke=0)

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(1)
    pdf.line(plot_left, plot_bottom - 7, plot_right, plot_bottom - 7)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 10)
    for tick in (0.5, 0.6, 0.7):
        pdf.drawCentredString(scale(tick), plot_bottom - 22, f"{tick:.1f}")
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString((plot_left + plot_right) / 2, y + 5, "Scaling exponent")


def prepare_crops(work_dir: Path) -> dict[str, Path]:
    prediction = ROOT / "output" / "manuscript" / "figure_prediction.png"
    required = [prediction, FIRED_SEQUENCES, FIRED_GEOMETRY, MODEL_RUNS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing poster source figures: " + ", ".join(missing))

    crops = {
        "forecast": crop_fraction(
            prediction, work_dir / "forecast.png", (0.012, 0.055, 0.500, 0.505)
        ),
        "acceleration": crop_fraction(
            prediction, work_dir / "acceleration.png", (0.515, 0.500, 0.985, 0.960)
        ),
    }
    erase_fraction(crops["forecast"], (0.000, 0.000, 0.055, 0.075))
    erase_fraction(crops["acceleration"], (0.000, 0.000, 0.045, 0.085))
    return crops


def build_poster(output: Path, work_dir: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    crops = prepare_crops(work_dir)
    fired_x, fired_y, fired_weights = load_fired_between_geometry()
    model_x, model_y = load_model_geometry()

    page_width, page_height = PAGE_SIZE
    pdf = canvas.Canvas(str(output), pagesize=PAGE_SIZE, pageCompression=1)
    pdf.setTitle("Real fires scale differently - and their geometry predicts what happens next")
    pdf.setAuthor("spread-vs-growth")
    pdf.setSubject("FIRED geometric scaling, life-cycle state, and prediction")

    pdf.setFillColor(BG)
    pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    margin = 54
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 54)
    pdf.drawString(
        margin,
        page_height - 90,
        "Real fires scale differently - and their geometry predicts",
    )
    pdf.setFont("Helvetica", 22)
    pdf.setFillColor(MUTED)
    pdf.drawString(
        margin,
        page_height - 126,
        "FIRED between-fire geometry approaches 2/3; existing smooth-front models remain near 1/2.",
    )
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(FIRE_DARK)
    pdf.drawRightString(
        page_width - margin,
        page_height - 94,
        "SPREAD VS GROWTH  |  FIRE METABOLISM",
    )
    pdf.setFillColor(FIRE)
    pdf.rect(margin, page_height - 154, page_width - 2 * margin, 5, fill=1, stroke=0)

    gutter = 46
    content_width = page_width - 2 * margin
    column_width = (content_width - 2 * gutter) / 3
    x_left = margin
    x_mid = margin + column_width + gutter
    x_right = margin + 2 * (column_width + gutter)
    top = page_height - 205

    draw_section_heading(pdf, "1", "Observed fires: near 2/3", x_left, top, FIRE)
    draw_log_density_plot(
        pdf,
        fired_x,
        fired_y,
        x_left,
        895,
        column_width,
        520,
        fit_weights=fired_weights,
        sample_label=f"{len(fired_x):,} fire-level means",
        blue_label="P proportional to A^(2/3), fit-anchored",
    )
    draw_estimand_comparison(pdf, x_left + 14, 635, column_width - 28, 225)
    pdf.setFillColor(FIRE_DARK)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(x_left + 12, 555, "Observed between-fire fit: 0.646 [0.639, 0.652].")
    draw_wrapped(
        pdf,
        "Across the locked 4,032-fire cohort, the regression lies near the two-thirds reference and far from one-half. The within-fire slope is lower (0.594), so this is a population geometry rather than a universal temporal law.",
        x_left + 12,
        528,
        column_width - 24,
        size=14,
        leading=18,
        color=MUTED,
    )

    draw_section_heading(pdf, "2", "Existing front models: near 1/2", x_mid, top, BLUE)
    draw_log_density_plot(
        pdf,
        model_x,
        model_y,
        x_mid,
        905,
        column_width,
        510,
        fit_weights=None,
        sample_label=f"{len(model_x):,} model outputs",
        blue_label="P proportional to A^(2/3), fit-anchored",
    )
    draw_model_slope_comparison(pdf, x_mid + 14, 635, column_width - 28, 235)
    pdf.setFillColor(BLUE_DARK)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(x_mid + 12, 602, "Baseline model cloud: 0.506 [0.505, 0.507].")
    draw_wrapped(
        pdf,
        "Exact ellipses, Huygens wavelets, normal-front level sets, and cellular-neighbor simulations cluster around one-half. These model families generate smooth or locally propagated fronts, not the observed population scaling.",
        x_mid + 12,
        575,
        column_width - 24,
        size=14,
        leading=18,
        color=MUTED,
    )

    draw_section_heading(pdf, "3", "Prediction on held-out fires", x_right, top, TEAL)
    draw_image_contain(pdf, crops["forecast"], x_right, 955, column_width, 460)
    draw_image_contain(pdf, crops["acceleration"], x_right, 600, column_width, 330)
    pdf.setFillColor(TEAL)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(x_right + 12, 548, "The signal is multivariate geometry, not an exponent flag.")
    draw_wrapped(
        pdf,
        "Full perimeter, excess perimeter, topology, and boundary change add information beyond area and recent dynamics. Uncertainty intervals resample whole fires.",
        x_right + 12,
        521,
        column_width - 24,
        size=14,
        leading=18,
        color=MUTED,
    )

    pdf.setStrokeColor(GRID)
    pdf.setLineWidth(1)
    for separator_x in (x_mid - gutter / 2, x_right - gutter / 2):
        pdf.line(separator_x, 505, separator_x, top + 28)

    band_y = 335
    band_height = 140
    pdf.setFillColor(HexColor("#F2F3F1"))
    pdf.rect(margin, band_y, content_width, band_height, fill=1, stroke=0)
    metric_width = content_width / 4
    draw_metric(pdf, margin + 18, band_y + 8, metric_width - 28, "0.646", "observed between-fire fit", FIRE)
    draw_metric(pdf, margin + metric_width + 18, band_y + 8, metric_width - 28, "0.506", "classical baseline model cloud", BLUE)
    draw_metric(pdf, margin + 2 * metric_width + 18, band_y + 8, metric_width - 28, "13.3%", "lower seven-day error vs area dynamics", TEAL)
    draw_metric(pdf, margin + 3 * metric_width + 18, band_y + 8, metric_width - 28, "0.790", "balanced accuracy for future acceleration", GOLD)

    lower_y = 76
    lower_height = 225
    lower_gutter = 28
    lower_width = (content_width - lower_gutter) / 2
    pdf.setFillColor(TEAL_PALE)
    pdf.rect(margin, lower_y, lower_width, lower_height, fill=1, stroke=0)
    pdf.setFillColor(BLUE_PALE)
    pdf.rect(
        margin + lower_width + lower_gutter,
        lower_y,
        lower_width,
        lower_height,
        fill=1,
        stroke=0,
    )

    pdf.setFillColor(TEAL)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin + 22, lower_y + 182, "What the evidence supports")
    support_lines = [
        "Observed fire populations scale differently from smooth-front benchmarks.",
        "Mapped whole-fire geometry adds reproducible future-area skill.",
        "Geometry improves prediction of near-term acceleration.",
    ]
    pdf.setFont("Helvetica", 14)
    pdf.setFillColor(INK)
    y = lower_y + 145
    for line in support_lines:
        pdf.setFillColor(TEAL)
        pdf.circle(margin + 29, y + 4, 4, fill=1, stroke=0)
        pdf.setFillColor(INK)
        pdf.drawString(margin + 43, y, line)
        y -= 34

    right_box_x = margin + lower_width + lower_gutter
    pdf.setFillColor(BLUE_DARK)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(right_box_x + 22, lower_y + 182, "What keeps the claim honest")
    missing_lines = [
        "The comparison is against matched smooth-front benchmark families.",
        "An amplified heterogeneous level-set emulator can approach two-thirds.",
        "Exponent alone is not mechanism; prospective matched tests remain.",
    ]
    pdf.setFont("Helvetica", 14)
    y = lower_y + 145
    for line in missing_lines:
        pdf.setFillColor(BLUE_DARK)
        pdf.circle(right_box_x + 29, y + 4, 4, fill=1, stroke=0)
        pdf.setFillColor(INK)
        pdf.drawString(right_box_x + 43, y, line)
        y -= 34

    pdf.setFont("Helvetica", 9.5)
    pdf.setFillColor(MUTED)
    pdf.drawString(
        margin,
        36,
        "FIRED cohort: 4,032 fires; held-out years 2016-2020. Classical comparison includes ellipse, Huygens, normal-front level-set, and cellular benchmarks.",
    )
    pdf.drawRightString(
        page_width - margin,
        36,
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
