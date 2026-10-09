#!/usr/bin/env python3
"""Extract real-footprint spatial-reorganization metrics from FIRED.

This is the restartable geospatial stage of the integrated experiment. It must
run in an environment with GeoPandas, Shapely, Rasterio, and PyArrow. The
repository's numerical analysis environment intentionally keeps those optional
dependencies separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Point, box, mapping
from shapely.ops import unary_union

from fire_metabolism.spatial_reorganization import (
    deterministic_support,
    sliced_wasserstein,
    unbalanced_sinkhorn_distance,
)


SEED = 20261008
PRIMARY_RESOLUTION_M = 500.0
PARTITION_SAMPLE = 300
SNAPSHOTS = (5, 7, 10, 14, 21)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fired-gpkg", type=Path,
        default=Path("../cubedynamics/artifacts/fire-vase-gridmet-real/fired-cache/"
                     "fired_conus-ak_daily_nov2001-march2021.gpkg"),
    )
    parser.add_argument(
        "--local-slopes", type=Path,
        default=Path("outputs/geometric_attractor_validation/local_slope_estimates.csv.gz"),
    )
    parser.add_argument(
        "--sequences", type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("outputs/integrated_geometry_transport"),
    )
    parser.add_argument("--events-per-partition", type=int, default=PARTITION_SAMPLE)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def partition(year: int) -> str:
    if year <= 2012:
        return "development"
    if year <= 2015:
        return "calibration"
    return "held_out"


def stable_sample(frame: pd.DataFrame, n: int) -> pd.DataFrame:
    """Outcome-blind, partition-stratified sample locked by the project seed."""
    rng = np.random.default_rng(SEED)
    chosen: list[int] = []
    for part in ("development", "calibration", "held_out"):
        ids = np.sort(frame.loc[frame.partition.eq(part), "id"].unique())
        if len(ids) > n:
            ids = np.sort(rng.choice(ids, size=n, replace=False))
        chosen.extend(ids.tolist())
    result = frame[frame.id.isin(chosen)].copy()
    result["primary_sample"] = True
    return result


def area_matched_buffer(start, target_area: float):
    """Isotropically dilate ``start`` until its area matches the observation."""
    if target_area <= start.area * (1 + 1e-10):
        return start, 0.0
    low, high = 0.0, max(np.sqrt((target_area - start.area) / np.pi), 10.0)
    for _ in range(30):
        if start.buffer(high).area >= target_area:
            break
        high *= 2.0
    for _ in range(24):
        middle = 0.5 * (low + high)
        if start.buffer(middle).area < target_area:
            low = middle
        else:
            high = middle
    return start.buffer(high), high


def raster_pair(actual, reference, resolution_m: float, max_side: int = 320):
    minx, miny, maxx, maxy = unary_union([actual, reference]).bounds
    extent = max(maxx - minx, maxy - miny)
    effective = max(float(resolution_m), extent / max(max_side - 6, 1))
    pad = 2 * effective
    minx, miny, maxx, maxy = minx - pad, miny - pad, maxx + pad, maxy + pad
    width = max(3, int(np.ceil((maxx - minx) / effective)))
    height = max(3, int(np.ceil((maxy - miny) / effective)))
    transform = from_origin(minx, maxy, effective, effective)
    kwargs = dict(out_shape=(height, width), transform=transform, fill=0, dtype="uint8", all_touched=True)
    actual_mask = rasterize([(mapping(actual), 1)], **kwargs).astype(bool)
    reference_mask = rasterize([(mapping(reference), 1)], **kwargs).astype(bool)
    if not actual_mask.any() or not reference_mask.any():
        raise ValueError("rasterization produced an empty footprint")
    # deterministic_support uses a lower-left convention; reflection does not
    # alter distances because both masks use the same transform.
    support_a, _ = deterministic_support(
        actual_mask, pixel_size=effective, origin=(minx, miny), max_points=128
    )
    support_b, _ = deterministic_support(
        reference_mask, pixel_size=effective, origin=(minx, miny), max_points=128
    )
    return actual_mask, reference_mask, support_a, support_b, effective


def component_hole_counts(geometry) -> tuple[int, int]:
    polygons = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    return len(polygons), int(sum(len(p.interiors) for p in polygons))


def transition_metrics(start, actual, *, resolution_m: float) -> dict[str, float | int | bool]:
    null, radius = area_matched_buffer(start, actual.area)
    amask, nmask, apoints, npoints, effective = raster_pair(actual, null, resolution_m)
    aweights = np.full(len(apoints), actual.area / len(apoints))
    nweights = np.full(len(npoints), null.area / len(npoints))
    sw1 = sliced_wasserstein(apoints, aweights, npoints, nweights, order=1)
    sw2 = sliced_wasserstein(apoints, aweights, npoints, nweights, order=2)
    sw2_centered = sliced_wasserstein(
        apoints, aweights, npoints, nweights, order=2, translation_normalized=True
    )
    # A smaller support keeps KL-relaxed transport fast while preserving its
    # role as a sensitivity analysis rather than the primary estimator.
    ai = np.linspace(0, len(apoints) - 1, min(32, len(apoints))).round().astype(int)
    ni = np.linspace(0, len(npoints) - 1, min(32, len(npoints))).round().astype(int)
    uot = unbalanced_sinkhorn_distance(
        apoints[ai], aweights[ai], npoints[ni], nweights[ni],
        epsilon=0.05, mass_penalty=1.0,
        scale=max(np.sqrt(actual.area), effective), max_iterations=150,
        tolerance=1e-6,
    )
    intersection = actual.intersection(null).area
    union = actual.union(null).area
    symdiff = actual.symmetric_difference(null).area
    actual_components, actual_holes = component_hole_counts(actual)
    null_components, null_holes = component_hole_counts(null)
    scale_km = np.sqrt(actual.area) / 1000.0
    return {
        "start_area_km2": start.area / 1e6,
        "target_area_km2": actual.area / 1e6,
        "delta_area_km2": (actual.area - start.area) / 1e6,
        "null_area_km2": null.area / 1e6,
        "null_area_relative_error": (null.area - actual.area) / max(actual.area, 1.0),
        "dilation_radius_km": radius / 1000.0,
        "balanced_sw1_km": sw1 / 1000.0,
        "balanced_sw2_km": sw2 / 1000.0,
        "translation_normalized_sw2_km": sw2_centered / 1000.0,
        "unbalanced_kl_distance_km": uot.distance / 1000.0,
        "reorganization_primary": (sw2 / 1000.0) / max(scale_km, 1e-9),
        "reorganization_centered": (sw2_centered / 1000.0) / max(scale_km, 1e-9),
        "centroid_displacement_km": actual.centroid.distance(null.centroid) / 1000.0,
        "hausdorff_distance_km": actual.hausdorff_distance(null) / 1000.0,
        "symmetric_difference_km2": symdiff / 1e6,
        "iou": intersection / max(union, 1.0),
        "actual_perimeter_km": actual.length / 1000.0,
        "null_perimeter_km": null.length / 1000.0,
        "perimeter_difference_km": (actual.length - null.length) / 1000.0,
        "actual_excess_perimeter": actual.length / max(2 * np.sqrt(np.pi * actual.area), 1.0),
        "null_excess_perimeter": null.length / max(2 * np.sqrt(np.pi * null.area), 1.0),
        "component_difference": actual_components - null_components,
        "hole_difference": actual_holes - null_holes,
        "raster_resolution_requested_m": resolution_m,
        "raster_resolution_effective_m": effective,
        "raster_cells": int(amask.size),
        "actual_support_points": len(apoints),
        "null_support_points": len(npoints),
        "uot_converged": uot.converged,
        "uot_iterations": uot.iterations,
        "uot_marginal_error": uot.marginal_error,
    }


def build_pair_roles(local: pd.DataFrame, geometry_days: np.ndarray) -> dict[tuple[int, int], set[str]]:
    pairs: dict[tuple[int, int], set[str]] = {}
    days = np.sort(np.unique(geometry_days.astype(int)))
    for left, right in zip(local.event_day.iloc[:-1], local.event_day.iloc[1:]):
        if right > left:
            pairs.setdefault((int(left), int(right)), set()).add("attractor_forward")
    for snapshot in SNAPSHOTS:
        end_candidates = days[days <= snapshot]
        start_candidates = days[days <= snapshot - 3]
        if len(end_candidates) and len(start_candidates):
            pair = (int(start_candidates[-1]), int(end_candidates[-1]))
            if pair[1] > pair[0]:
                pairs.setdefault(pair, set()).add(f"prediction_origin_{snapshot}")
    return pairs


def cumulative_geometries(event: gpd.GeoDataFrame) -> dict[int, object]:
    cumulative = None
    result = {}
    for day, rows in event.sort_values("event_day").groupby("event_day", sort=True):
        daily = unary_union(rows.geometry.tolist())
        cumulative = daily if cumulative is None else cumulative.union(daily)
        if not cumulative.is_valid:
            cumulative = cumulative.buffer(0)
        result[int(day)] = cumulative
    return result


def synthetic_benchmarks() -> pd.DataFrame:
    start = Point(0, 0).buffer(2000, resolution=24)
    targets = {
        "isotropic_expansion": start.buffer(1200),
        "directional_expansion": start.union(box(1500, -700, 7000, 700)),
        "finger_formation": start.union(box(1500, -180, 9000, 180)),
        "hole_filling": Point(0, 0).buffer(3200, resolution=24),
        "component_merging": start.union(Point(5000, 0).buffer(1400)).union(box(1600, -300, 3600, 300)),
        "fragmented_spotting": unary_union([start, Point(5000, 0).buffer(700), Point(-3500, 3000).buffer(550)]),
        "translated_shape_growth": start.union(Point(4200, 0).buffer(1800)),
    }
    rows = []
    for name, target in targets.items():
        row = transition_metrics(start, target, resolution_m=250.0)
        row["scenario"] = name
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    local_all = pd.read_csv(args.local_slopes)
    local_all = local_all[local_all.estimator.eq("rolling_ols_7")].copy()
    local_all["partition"] = local_all.ig_year.map(partition)
    sequences = pd.read_csv(args.sequences)
    event_index = sequences[["id", "ig_year"]].drop_duplicates()
    event_index["partition"] = event_index.ig_year.map(partition)
    n = 8 if args.smoke else args.events_per_partition
    sampled_index = stable_sample(event_index, n)

    duration = sequences.groupby("id", as_index=False).event_day.max().rename(columns={"event_day": "duration_days"})
    long_ids = duration.loc[duration.duration_days >= 42, "id"]
    descriptive_long = event_index[event_index.id.isin(long_ids)].copy()
    descriptive_long["primary_sample"] = descriptive_long.id.isin(sampled_index.id)
    selected_index = pd.concat([sampled_index, descriptive_long], ignore_index=True).drop_duplicates("id")
    selected_ids = np.sort(selected_index.id.unique())

    source = args.fired_gpkg.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"FIRED daily polygon source not found: {source}")
    where = "id IN (" + ",".join(map(str, selected_ids)) + ")"
    daily = gpd.read_file(source, where=where, engine="pyogrio")
    daily = daily[["id", "event_day", "geometry"]]

    rows: list[dict[str, object]] = []
    resolution_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    local_lookup = {int(i): g.sort_values("event_day") for i, g in local_all.groupby("id")}
    index_lookup = selected_index.set_index("id")
    for count, (event_id, event) in enumerate(daily.groupby("id", sort=True), start=1):
        event_id = int(event_id)
        geometries = cumulative_geometries(event)
        local = local_lookup.get(event_id, pd.DataFrame(columns=["event_day"]))
        pairs = build_pair_roles(local, np.array(list(geometries)))
        for (start_day, future_day), roles in pairs.items():
            if start_day not in geometries or future_day not in geometries:
                continue
            try:
                metrics = transition_metrics(
                    geometries[start_day], geometries[future_day],
                    resolution_m=PRIMARY_RESOLUTION_M,
                )
                info = index_lookup.loc[event_id]
                row = {
                    "id": event_id,
                    "ig_year": int(info.ig_year),
                    "partition": str(info.partition),
                    "primary_sample": bool(info.primary_sample),
                    "origin_day": start_day,
                    "future_day": future_day,
                    "actual_lead_days": future_day - start_day,
                    "roles": ";".join(sorted(roles)),
                    **metrics,
                }
                rows.append(row)
                if hashlib.sha1(f"{event_id}-{start_day}-{future_day}".encode()).digest()[0] < 5:
                    for resolution in (250.0, 500.0, 1000.0, 2000.0):
                        sensitive = transition_metrics(
                            geometries[start_day], geometries[future_day], resolution_m=resolution
                        )
                        resolution_rows.append({
                            "id": event_id, "origin_day": start_day,
                            "future_day": future_day, "resolution_m": resolution,
                            **sensitive,
                        })
            except Exception as exc:
                failures.append({
                    "id": event_id, "origin_day": start_day,
                    "future_day": future_day, "error": repr(exc),
                })
        if count % 50 == 0:
            print(f"processed {count}/{daily.id.nunique()} events; {len(rows)} transitions")

    transport = pd.DataFrame(rows)
    if transport.empty:
        raise RuntimeError("no FIRED transport transitions were computed")
    transport.to_parquet(output / "transport_transition_metrics.parquet", index=False)
    synthetic_benchmarks().to_csv(output / "transport_synthetic_benchmarks.csv", index=False)
    pd.DataFrame(resolution_rows).to_csv(output / "transport_resolution_sensitivity.csv", index=False)
    pd.DataFrame(failures).to_csv(output / "transport_failures.csv", index=False)
    selection = selected_index.merge(duration, on="id", how="left")
    selection.to_csv(output / "transport_event_sample.csv", index=False)
    report = {
        "status": "complete",
        "source": str(source),
        "source_size_bytes": source.stat().st_size,
        "events_in_locked_cohort": int(event_index.id.nunique()),
        "primary_sample_events": int(sampled_index.id.nunique()),
        "descriptive_long_events": int(descriptive_long.id.nunique()),
        "source_rows_loaded": int(len(daily)),
        "transport_transitions": int(len(transport)),
        "transport_events": int(transport.id.nunique()),
        "failures": int(len(failures)),
        "primary_resolution_m": PRIMARY_RESOLUTION_M,
        "primary_metric": "balanced sliced W2(actual, area-matched isotropic dilation) / sqrt(target area)",
        "random_seed": SEED,
    }
    (output / "transport_extraction_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
