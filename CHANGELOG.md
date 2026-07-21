# Changelog

## Unreleased

- Retargeted the repository from the starter template to `spread-vs-growth`.
- Added project documentation for the ESA 2026 Fire Metabolism storyboard.
- Added a lightweight workflow for long-running figure and animation work.
- Added project-specific agent instructions and a prompt log.
- Added a script for rendering ink diffusion and slime-mold source videos side by side.
- Added a script for tracing perimeter polygons and measuring area/perimeter growth through video stages.
- Added log area-vs-perimeter plotting for the video perimeter measurements.
- Added a Tier-1 fire-model perimeter-area scaling workflow with benchmark/emulator models, tests, fits, figures, and actual-model status logs.
- Cloned and attempted real external fire-model software runs: completed an ELMFIRE constant-wind tutorial run and recorded a Cell2Fire native build failure due to missing Boost headers.
- Added a dense model-output hexbin plotting script styled after the reference event-size plot; the homogeneous/anisotropic model cloud fit is near the `1/2` line.
- Added configurable heterogeneity levels for the dense model hexbin plot and generated a higher-variance heterogeneous comparison.
- Added model filtering for dense hexbin plots and generated a level-set-only heterogeneous comparison.
- Generated a matching heterogeneous hexbin comparison with the level-set emulator excluded.
- Added a complete model-run handoff dataset export with split level-set and non-level-set CSVs, fit summaries, and a zip archive.
- Added a calibrated shallow grass-fire animation workflow that renders diagnostic and clean MP4s with measured perimeter-area scaling near `P proportional to A^(2/3)`.
- Added a flatter perspective fire-growth explainer across grassland, forest, and WUI contexts using the calibrated two-thirds footprint.
- Added an option to hide the `2/3` and `3/4` reference lines in dense model hexbin plots and regenerated the no-level-set comparison.
- Added a no-level-set model hexbin reveal animation that accumulates the model cloud from left to right while keeping only the `1/2` reference and fitted-slope lines.
- Corrected the no-level-set hexbin `1/2` reference line to share the fitted model-cloud intercept, while keeping exponent `0.5`; the model-fit line uses the fitted log-log intercept and slope.
- Added a data-free red/blue reference-line MP4 that draws only the `1/2` and `2/3` perimeter-area scaling lines.
- Updated the reference-line MP4 so the red `1/2` line is present from the first frame and the thicker blue `2/3` line animates on.
- Added a helper to overlay the blue `2/3` reference line onto an existing event-hexbin PNG.
- Adjusted the event-hexbin blue `2/3` overlay to use a lower origin-like coefficient with a thicker, transparent cornflower-blue stroke.
- Updated side-by-side video output defaults for better media-player and presentation compatibility.
- Removed template-era workflows that synced from the starter repository or built a missing JupyterLab container.
