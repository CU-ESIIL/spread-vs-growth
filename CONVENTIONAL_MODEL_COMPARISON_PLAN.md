# Conventional Wildfire Model Comparison Plan

## Purpose

This plan defines how a future process-model comparison can be scientifically fair. It does not report a conventional-model result.

The target comparison is among persistence, empirical trajectory models, reduced growth laws, a flexible empirical benchmark, and a conventional spatial fire-spread model on the same fires, origins, information constraints, and outcome metrics.

## Current feasibility verdict

An event-matched conventional comparison is **not currently ready**.

- ELMFIRE was built and its official constant-wind tutorial completed successfully.
- The copied ELMFIRE output is a 400 by 400, 30 m synthetic tutorial raster and hourly isochrones; it is not associated with a FIRED event.
- Cell2Fire has not run because its native build lacks Boost headers.
- FIRED supplies retrospective daily polygons, dates, ignition coordinates, area, and land-cover/ecoregion attributes.
- This repository does not contain event-matched fuels, canopy structure, topography, hourly weather, fuel moisture, or suppression histories.
- A 37 GB GridMET cache exists in an adjacent project, but it is not yet a declared or provenance-documented dependency here.

Therefore the immediate deliverable should be an adapter and a development-event feasibility pilot, not a held-out performance claim.

## Fair comparison targets

All models should be reduced to the same output schema:

1. cumulative burned area at fixed future horizons;
2. incremental area growth for each horizon;
3. final mapped area only when the model includes an origin-safe termination forecast;
4. perimeter and footprint overlap only when both observed and predicted spatial geometry are available;
5. runtime and required input inventory.

Do not compare a process model's published rate-of-spread accuracy with this repository's final-area error. Those are different targets.

## Information tiers

| Tier | Inputs | Models eligible for comparison |
| --- | --- | --- |
| 0 | Current area only | Persistence, historical multiplier |
| 1 | FIRED area history through origin | Reduced laws, ridge, flexible empirical model |
| 2 | Tier 1 plus origin-available weather | Weather-augmented empirical and reduced models |
| 3 | Tier 2 plus origin geometry | Geometry-aware statistical models |
| 4 | Perimeter/ignition state, fuels, topography, weather, fuel moisture | ELMFIRE or another process model |

Performance and information requirements must be shown together. A Tier-4 process model should not be described as equivalent in input burden to an `(A, beta)` model.

## Adapter/API

### Forecast request

```text
event_id
model_id and model_version
origin_datetime
forecast_horizons
observed cumulative area history through origin
origin perimeter or ignition geometry, with CRS
weather path and time range available through/after origin
fuel and canopy rasters
elevation, slope, and aspect rasters
fuel-moisture initialization
model resolution and numerical settings
input provenance and checksums
```

### Forecast result

```text
event_id and origin
model_id and executable commit
cumulative area by horizon
incremental growth by horizon
predicted perimeter by horizon
optional footprint geometry by horizon
runtime and peak memory
warnings, failures, and domain-contact flags
all input and configuration checksums
```

The adapter must never attach observed post-origin geometry. Evaluation joins truth only after the model output is finalized.

## FIRED initialization questions

FIRED daily geometries are `MULTIPOLYGON` features in a metre-based sinusoidal CRS. Before process-model initialization, determine and test:

1. whether each geometry is a daily addition or a cumulative footprint;
2. how to union all observations through the origin without changing holes or disconnected components;
3. whether the process model can restart from an observed burned footprint/perimeter;
4. whether interior cells should be initialized as already burned, nonburnable, or assigned historical arrival times;
5. how a daily MODIS-derived origin time maps to an hourly process-model clock;
6. how to handle events whose mapped growth includes unobserved spotting or mergers;
7. how to construct a domain large enough to prevent boundary contact over the forecast horizon.

If ELMFIRE cannot restart from a snapshot perimeter, a run from the original ignition would require pre-origin weather and a calibration step. That is a different information regime and must not be compared as though it received the observed snapshot.

## Required external data

At minimum an event-matched process run needs:

- fuel model and canopy layers at a documented date and resolution;
- elevation, slope, and aspect;
- hourly wind speed and direction, temperature, and humidity;
- precipitation and fuel-moisture initialization or a documented moisture model;
- ignition or snapshot geometry and time;
- projection, grid, domain, and boundary-condition metadata;
- any suppression or barrier representation, or an explicit statement that these are absent.

Every external source needs a repository manifest covering access, format, spatial/temporal resolution, license, citation, preprocessing, and checksum policy.

## ELMFIRE feasibility sequence

### Adapter smoke test

- Parse the existing tutorial time-of-arrival raster and hourly isochrones.
- Convert arrival time to cumulative area, incremental growth, perimeter, and footprint records at standard horizons.
- Verify unit conversions, CRS handling, domain contact, and deterministic output.
- Label every result `tutorial_adapter_test`, never `FIRED comparison`.

### Development-event pilot

- Select 10-20 events from 2001-2012 only using predeclared size, duration, biome, and data-availability strata.
- Acquire or connect all required inputs with manifests.
- Test initialization from day-3 or day-5 observed geometry.
- Run one deterministic configuration first, then a small documented uncertainty ensemble if needed.
- Compare area and geometry at identical horizons.
- Do not inspect 2016-2020 process-model performance during adapter development.

### Calibration and validation

- Freeze executable commit, input products, parameter policy, resolution, and output adapter.
- Use 2013-2015 only for uncertainty calibration where needed.
- Run 2016-2020 only after the complete workflow passes development-event checks.
- Preserve failures and non-runs in denominators and machine-readable status tables.

## Cell2Fire status

Cell2Fire remains a candidate but is secondary until the Boost dependency is resolved and a real example completes. No Cell2Fire performance value should appear before its output adapter passes the same smoke tests as ELMFIRE.

## Common scoring

- Use identical event IDs, origins, and horizons for every paired comparison.
- Score cumulative-area absolute log error and absolute error.
- Score incremental-growth MAE and sMAPE with explicit zero handling.
- For spatial output, report intersection-over-union, area bias, exterior-perimeter error, and centroid displacement under a locked geometry convention.
- Bootstrap whole events and bootstrap paired error differences.
- Report non-convergence, missing inputs, domain contact, and adapter failures rather than dropping them silently.

## Complexity and cost reporting

Record for each model:

- number of input variables and distinct external data products;
- population-fitted and event-fitted parameters;
- spatial and temporal resolution;
- wall time, peak memory, and storage;
- manual preprocessing requirements;
- success/failure rate.

## Stop conditions

Do not proceed to a held-out conventional-model claim if any of the following remain unresolved:

- snapshot restart is unsupported or scientifically ambiguous;
- required weather, fuels, or topography are missing for a substantial fraction of events;
- the adapter cannot reproduce tutorial area/perimeter trajectories deterministically;
- process and statistical models receive incomparable future information;
- geometry conventions differ between prediction and truth;
- the event sample is selected after viewing validation performance.

## Immediate next implementation step

Build a read-only ELMFIRE tutorial adapter that produces the common forecast-result schema and validates cumulative area from the existing time-of-arrival raster. This is useful infrastructure but is not evidence that a conventional model predicts FIRED events.
