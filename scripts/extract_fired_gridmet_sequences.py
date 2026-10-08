#!/opt/homebrew/bin/python3
"""Extract centroid gridMET weather for eligible FIRED daily sequences.

This helper uses Homebrew GDAL's Python bindings so the project environment
does not need a second GDAL installation. Source NetCDF files must already be
cached locally. No network access is performed.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
from pathlib import Path

from osgeo import gdal, ogr, osr


VARIABLES = {
    "vpd_kpa": "vpd",
    "wind_speed_m_s": "vs",
    "fuel_moisture_100hr_pct": "fm100",
    "energy_release_component": "erc",
    "precipitation_mm": "pr",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-gpkg", type=Path, required=True)
    parser.add_argument("--gridmet-cache", type=Path, required=True)
    parser.add_argument(
        "--sequences",
        type=Path,
        default=Path("outputs/fired_prediction/fired_sequences.csv.gz"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/fired_missing_processes/gridmet_event_daily.csv.gz"),
    )
    return parser.parse_args()


def read_sequence_rows(path: Path) -> tuple[list[dict[str, object]], set[int]]:
    opener = gzip.open if path.suffix == ".gz" else open
    rows = []
    ids = set()
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            event_id = int(row["id"])
            date = dt.date.fromisoformat(row["date"])
            rows.append(
                {
                    "id": event_id,
                    "event_day": int(row["event_day"]),
                    "date": date,
                    "year": date.year,
                }
            )
            ids.add(event_id)
    if not rows:
        raise ValueError("the sequence table contains no rows")
    return rows, ids


def event_centroids(path: Path, ids: set[int]) -> dict[int, tuple[float, float]]:
    dataset = gdal.OpenEx(
        str(path.resolve()),
        gdal.OF_VECTOR | gdal.OF_READONLY,
        open_options=["IMMUTABLE=YES"],
    )
    if dataset is None:
        raise FileNotFoundError(path)
    layer = dataset.GetLayer(0)
    source = layer.GetSpatialRef().Clone()
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    target.ImportFromEPSG(4326)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source, target)
    name = layer.GetName().replace('"', '""')
    id_clause = ",".join(str(value) for value in sorted(ids))
    selected = dataset.ExecuteSQL(
        f'SELECT id, geom FROM "{name}" WHERE id IN ({id_clause})',
        dialect="SQLITE",
    )
    if selected is None:
        raise RuntimeError("GDAL could not select eligible event geometries")
    result = {}
    for feature in selected:
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.IsEmpty():
            continue
        centroid = geometry.Centroid()
        centroid.Transform(transform)
        result[int(feature["id"])] = (float(centroid.GetX()), float(centroid.GetY()))
    dataset.ReleaseResultSet(selected)
    dataset = None
    return result


def point_series(dataset, lon: float, lat: float) -> list[float | None]:
    transform = dataset.GetGeoTransform()
    pixel = int((lon - transform[0]) / transform[1])
    line = int((lat - transform[3]) / transform[5])
    if not (0 <= pixel < dataset.RasterXSize and 0 <= line < dataset.RasterYSize):
        return [None] * dataset.RasterCount
    array = dataset.ReadAsArray(pixel, line, 1, 1)
    if dataset.RasterCount == 1:
        array = array.reshape(1, 1, 1)
    values = []
    for index in range(dataset.RasterCount):
        band = dataset.GetRasterBand(index + 1)
        raw = float(array[index, 0, 0])
        nodata = band.GetNoDataValue()
        if nodata is not None and raw == nodata:
            values.append(None)
            continue
        scale = band.GetScale() if band.GetScale() is not None else 1.0
        offset = band.GetOffset() if band.GetOffset() is not None else 0.0
        values.append(raw * scale + offset)
    return values


def main() -> int:
    args = parse_args()
    gdal.UseExceptions()
    rows, ids = read_sequence_rows(args.sequences.expanduser().resolve())
    centroids = event_centroids(args.events_gpkg.expanduser().resolve(), ids)
    records = {
        (int(row["id"]), int(row["event_day"])): {
            "id": int(row["id"]),
            "event_day": int(row["event_day"]),
            "date": row["date"].isoformat(),
            "centroid_lon": centroids.get(int(row["id"]), (None, None))[0],
            "centroid_lat": centroids.get(int(row["id"]), (None, None))[1],
        }
        for row in rows
    }
    rows_by_year: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        rows_by_year.setdefault(int(row["year"]), []).append(row)

    cache = args.gridmet_cache.expanduser().resolve()
    for year, year_rows in sorted(rows_by_year.items()):
        for output_name, short_name in VARIABLES.items():
            path = cache / f"{short_name}_{year}.nc"
            if not path.exists():
                continue
            dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
            if dataset is None:
                raise RuntimeError(f"could not open {path}")
            by_event: dict[int, list[dict[str, object]]] = {}
            for row in year_rows:
                by_event.setdefault(int(row["id"]), []).append(row)
            for event_id, event_rows in by_event.items():
                point = centroids.get(event_id)
                if point is None:
                    continue
                series = point_series(dataset, *point)
                for row in event_rows:
                    day_index = int(row["date"].timetuple().tm_yday) - 1
                    if 0 <= day_index < len(series):
                        records[(event_id, int(row["event_day"]))][output_name] = series[
                            day_index
                        ]
            dataset = None

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "event_day",
        "date",
        "centroid_lon",
        "centroid_lat",
        *VARIABLES,
    ]
    with gzip.open(output, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for key in sorted(records):
            writer.writerow(records[key])
    complete = sum(
        all(record.get(name) is not None for name in VARIABLES)
        for record in records.values()
    )
    print(f"Wrote {output}")
    print(f"Eligible events: {len(ids)}")
    print(f"Rows: {len(records)}; complete climate rows: {complete}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
