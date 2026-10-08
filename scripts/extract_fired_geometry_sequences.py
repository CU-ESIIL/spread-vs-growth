#!/opt/homebrew/bin/python3
"""Extract cumulative FIRED polygon geometry for eligible event sequences.

This helper uses Homebrew GDAL's Python bindings because the project virtual
environment intentionally does not carry a second GDAL installation. It reads
the eligible event ids from the existing compressed FIRED sequence table and
writes one geometry record for every FIRED detection day. Calendar-day gaps are
filled later when these measurements are joined to the area sequences.
"""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from osgeo import gdal, ogr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fired-gpkg", type=Path, required=True)
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/fired_lifecycle_prediction/fired_geometry_sequences.csv.gz"),
    )
    return parser.parse_args()


def eligible_ids(path: Path) -> list[int]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        ids = {int(row["id"]) for row in reader}
    if not ids:
        raise ValueError("the sequence table contains no event ids")
    return sorted(ids)


def polygon_metrics(geometry: ogr.Geometry) -> tuple[float, float, int, int]:
    """Return total boundary, exterior boundary, components, and holes."""
    name = geometry.GetGeometryName().upper()
    total = geometry.Boundary().Length()
    exterior = 0.0
    components = 0
    holes = 0
    if name == "POLYGON":
        exterior = geometry.GetGeometryRef(0).Length()
        components = 1
        holes = max(0, geometry.GetGeometryCount() - 1)
    elif name == "MULTIPOLYGON":
        for index in range(geometry.GetGeometryCount()):
            polygon = geometry.GetGeometryRef(index)
            if polygon is None or polygon.GetGeometryCount() == 0:
                continue
            exterior += polygon.GetGeometryRef(0).Length()
            components += 1
            holes += max(0, polygon.GetGeometryCount() - 1)
    else:
        raise ValueError(f"unexpected cumulative geometry type: {name}")
    return total, exterior, components, holes


def union_geometries(geometries: list[ogr.Geometry]) -> ogr.Geometry:
    merged = geometries[0]
    for geometry in geometries[1:]:
        merged = merged.Union(geometry)
        if merged is None:
            raise RuntimeError("GDAL returned an empty daily union")
    return merged


def main() -> int:
    args = parse_args()
    source = args.fired_gpkg.expanduser().resolve()
    sequences = args.sequences.expanduser().resolve()
    output = args.output.expanduser().resolve()
    ids = eligible_ids(sequences)

    gdal.UseExceptions()
    dataset = gdal.OpenEx(
        str(source),
        gdal.OF_VECTOR | gdal.OF_READONLY,
        open_options=["IMMUTABLE=YES"],
    )
    if dataset is None:
        raise FileNotFoundError(source)
    layer = dataset.GetLayer(0)
    layer_name = layer.GetName().replace('"', '""')
    id_clause = ",".join(str(event_id) for event_id in ids)
    sql = (
        f'SELECT id, event_day, geom FROM "{layer_name}" '
        f"WHERE id IN ({id_clause}) ORDER BY id, event_day"
    )
    selected = dataset.ExecuteSQL(sql, dialect="SQLITE")
    if selected is None:
        raise RuntimeError("GDAL could not create the ordered FIRED geometry query")

    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "event_day",
        "daily_polygon_area_km2",
        "daily_total_perimeter_km",
        "daily_exterior_perimeter_km",
        "daily_component_count",
        "daily_hole_count",
        "polygon_area_km2",
        "total_perimeter_km",
        "exterior_perimeter_km",
        "component_count",
        "hole_count",
    ]
    current_id: int | None = None
    current_day: int | None = None
    day_geometries: list[ogr.Geometry] = []
    cumulative: ogr.Geometry | None = None
    rows_written = 0

    def flush_day(writer: csv.DictWriter) -> None:
        nonlocal cumulative, day_geometries, rows_written
        if current_id is None or current_day is None or not day_geometries:
            return
        daily = union_geometries(day_geometries)
        daily_total, daily_exterior, daily_components, daily_holes = polygon_metrics(
            daily
        )
        cumulative = daily if cumulative is None else cumulative.Union(daily)
        if cumulative is None:
            raise RuntimeError(f"cumulative union failed for event {current_id}")
        total, exterior, components, holes = polygon_metrics(cumulative)
        writer.writerow(
            {
                "id": current_id,
                "event_day": current_day,
                "daily_polygon_area_km2": daily.Area() / 1_000_000.0,
                "daily_total_perimeter_km": daily_total / 1000.0,
                "daily_exterior_perimeter_km": daily_exterior / 1000.0,
                "daily_component_count": daily_components,
                "daily_hole_count": daily_holes,
                "polygon_area_km2": cumulative.Area() / 1_000_000.0,
                "total_perimeter_km": total / 1000.0,
                "exterior_perimeter_km": exterior / 1000.0,
                "component_count": components,
                "hole_count": holes,
            }
        )
        rows_written += 1
        day_geometries = []

    with gzip.open(output, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for feature in selected:
            event_id = int(feature["id"])
            event_day = int(feature["event_day"])
            if current_id is None:
                current_id, current_day = event_id, event_day
            elif event_id != current_id or event_day != current_day:
                flush_day(writer)
                if event_id != current_id:
                    cumulative = None
                current_id, current_day = event_id, event_day
            geometry = feature.GetGeometryRef()
            if geometry is not None and not geometry.IsEmpty():
                day_geometries.append(geometry.Clone())
        flush_day(writer)

    dataset.ReleaseResultSet(selected)
    dataset = None
    print(f"Wrote {output}")
    print(f"Eligible events: {len(ids)}")
    print(f"Detection-day geometry rows: {rows_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
