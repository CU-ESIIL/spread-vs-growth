"""Create a side-by-side video from the raw ink and slime-mold clips."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from tqdm import tqdm

try:
    import imageio.v2 as imageio
except ImportError as exc:  # pragma: no cover - exercised only when deps are absent.
    raise SystemExit(
        "Missing dependency: imageio. Install project requirements with "
        "`python -m pip install -r requirements.txt`."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEFT = PROJECT_ROOT / "data" / "raw" / "3024109-hd_1920_1080_25fps.mp4"
DEFAULT_RIGHT = (
    PROJECT_ROOT / "data" / "raw" / "Australian_physarum_polycephalum_timelapse.webm"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "animations" / "ink_vs_slime_mold.mp4"


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def reader_fps(reader: Any, fallback: float) -> float:
    meta = reader.get_meta_data()
    fps = meta.get("fps")
    if fps and math.isfinite(float(fps)) and float(fps) > 0:
        return float(fps)
    return fallback


def reader_frame_count(reader: Any) -> int | None:
    try:
        count = reader.count_frames()
    except Exception:
        count = None

    if count is not None and math.isfinite(count) and count > 0:
        return int(count)

    meta = reader.get_meta_data()
    nframes = meta.get("nframes")
    if isinstance(nframes, (int, float)) and math.isfinite(nframes) and nframes > 0:
        return int(nframes)
    return None


def fit_frame(frame: np.ndarray, size: tuple[int, int], mode: str) -> Image.Image:
    """Resize a frame to a fixed panel size using contain or cover semantics."""
    target_w, target_h = size
    image = Image.fromarray(frame).convert("RGB")
    src_w, src_h = image.size

    if mode == "cover":
        scale = max(target_w / src_w, target_h / src_h)
    else:
        scale = min(target_w / src_w, target_h / src_h)

    resized_w = max(1, round(src_w * scale))
    resized_h = max(1, round(src_h * scale))
    resized = image.resize((resized_w, resized_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (target_w, target_h), "white")
    offset_x = (target_w - resized_w) // 2
    offset_y = (target_h - resized_h) // 2
    canvas.paste(resized, (offset_x, offset_y))

    if mode == "cover":
        left = max(0, (resized_w - target_w) // 2)
        top = max(0, (resized_h - target_h) // 2)
        canvas = resized.crop((left, top, left + target_w, top + target_h))

    return canvas


def side_by_side(
    left_path: Path,
    right_path: Path,
    output_path: Path,
    panel_width: int,
    panel_height: int,
    fps: float,
    duration: float | None,
    fit: str,
) -> None:
    if not left_path.exists():
        raise FileNotFoundError(f"Left video not found: {left_path}")
    if not right_path.exists():
        raise FileNotFoundError(f"Right video not found: {right_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    left_reader = imageio.get_reader(left_path)
    right_reader = imageio.get_reader(right_path)

    try:
        left_fps = reader_fps(left_reader, fps)
        right_fps = reader_fps(right_reader, fps)
        left_count = reader_frame_count(left_reader)
        right_count = reader_frame_count(right_reader)

        if duration is None:
            if left_count is None or right_count is None:
                raise ValueError(
                    "Could not determine both video lengths. Pass `--duration SECONDS`."
                )
            duration = min(left_count / left_fps, right_count / right_fps)

        frame_total = max(1, math.floor(duration * fps))
        writer = imageio.get_writer(
            output_path,
            fps=fps,
            codec="libx264",
            pixelformat="yuv420p",
            output_params=[
                "-movflags",
                "+faststart",
                "-profile:v",
                "main",
                "-level",
                "4.0",
            ],
            quality=8,
            macro_block_size=1,
        )

        try:
            for output_index in tqdm(range(frame_total), desc="Rendering frames"):
                t = output_index / fps
                left_index = min(math.floor(t * left_fps), (left_count or 1) - 1)
                right_index = min(math.floor(t * right_fps), (right_count or 1) - 1)

                left_frame = left_reader.get_data(left_index)
                right_frame = right_reader.get_data(right_index)

                left_panel = fit_frame(left_frame, (panel_width, panel_height), fit)
                right_panel = fit_frame(right_frame, (panel_width, panel_height), fit)

                canvas = Image.new("RGB", (panel_width * 2, panel_height), "white")
                canvas.paste(left_panel, (0, 0))
                canvas.paste(right_panel, (panel_width, 0))
                writer.append_data(np.asarray(canvas))
        finally:
            writer.close()
    finally:
        left_reader.close()
        right_reader.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stitch the ink diffusion video on the left and the slime-mold growth "
            "video on the right into one side-by-side MP4."
        )
    )
    parser.add_argument("--left", type=Path, default=DEFAULT_LEFT, help="left video path")
    parser.add_argument("--right", type=Path, default=DEFAULT_RIGHT, help="right video path")
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="output MP4 path"
    )
    parser.add_argument("--panel-width", type=positive_int, default=960)
    parser.add_argument("--panel-height", type=positive_int, default=1080)
    parser.add_argument("--fps", type=positive_float, default=25)
    parser.add_argument(
        "--duration",
        type=positive_float,
        default=None,
        help="seconds to render; defaults to the shorter source video",
    )
    parser.add_argument(
        "--fit",
        choices=("contain", "cover"),
        default="contain",
        help="contain preserves the full frame; cover fills each panel by cropping",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        side_by_side(
            left_path=args.left,
            right_path=args.right,
            output_path=args.output,
            panel_width=args.panel_width,
            panel_height=args.panel_height,
            fps=args.fps,
            duration=args.duration,
            fit=args.fit,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
