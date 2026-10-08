# Changelog

## 2026-10-08 - Lean formal audit of the SI mathematical kernel

- Added a pinned Lean 4.19.0 + Mathlib 4.19.0 project under `FireProof/` with modules for scaling, growth, kinematics, active boundary, finite fuel, matching, connectivity, metabolism, identifiability, and dimensional bookkeeping.
- Proved the core algebraic and calculus consequences without `sorry` or `admit`, including the conditional `4/3 -> 2/3` bridge, constant-beta cube-root solution, matching optimum, fuel bounds, equilibrium threshold, and local-slope decomposition.
- Isolated the moving-boundary transport identity as the sole custom scientific axiom instead of silently treating it as a Lean theorem.
- Added a claim-by-claim audit, assumptions inventory, formal counterexample, scientific summary, and reproducible axiom-audit script.
- Formalized why a measured `2/3` slope does not identify a fixed `2/3` geometric exponent and why no-crossing/invariance claims require continuity and uniqueness or barrier assumptions beyond boundary signs.
- Verified the complete project with `lake build` and `bash scripts/audit.sh`.

## 2026-10-05 - Missing-process tests and revised FIRED evidence report

- Added daily gridMET extraction for 4,032 FIRED events, with source, citation, access, reuse uncertainty, and limitations recorded in `data/gridmet-source.yml`.
- Added held-out tests of recent weather, a newly burned-boundary active-front proxy, and an observed next-day-weather oracle diagnostic.
- Found that past weather plus the front proxy improves day-7 persistent-regime AUC from 0.801 to 0.822 but only reduces persistent death-day MAE from 13.13 to 12.57 days; observed next-day weather reduces it only to 12.51 days.
- Found no Holm-adjusted terminal-weather difference between gradual and abrupt early-ending candidates using daily centroid gridMET.
- Confirmed that abrupt-ending enrichment is robust to four terminal-window definitions, with odds ratios from 2.95 to 6.07.
- Revised the evidence report to 31 pages with a missing-process closure audit, three new QA figures, stronger interpretation limits, and prioritized fuel-connectivity and suppression-linkage tests.
- Verified 120 tests and 10 subtests.

## 2026-10-05 - Complete FIRED prediction evidence report

- Added a reproducible 28-page report consolidating short-horizon, final-outcome, geometry/lifecycle, long-fire, state-survival, persistent-regime, damage, potential-to-realization, and early-termination analyses.
- Distinguished temporally held-out validation, retrospective oracle diagnostics, and synthetic first-principles checks throughout the report.
- Added a persistent-regime classifier and regime-specific death models, showing that day-5 long-fire death MAE falls from 13.13 to 6.33 days when persistence is known retrospectively.
- Tested accumulated growth-derived damage terms and found near-zero incremental prediction value beyond geometry and state.
- Added a day-7 persistent-course area model and found that predicted-persistent fires ending early realize a median 40.8% of that course, compared with 115.7% among high-confidence true persistent fires.
- Added terminal-growth diagnostics showing a mixture of gradual-decline-like and abrupt-truncation-like endings; abrupt signatures are 6.07 times as likely among early-ending candidates as among true persistent controls.
- Exported and qualified external-termination-like candidates for future linkage without interpreting them as suppression labels.
- Verified the repository with 116 passing tests and 10 passing subtests and visually inspected all 28 rendered report pages.

## 2026-10-05 - FIRED geometry-informed life-cycle prediction

- Added cumulative FIRED polygon unions and measurements of total perimeter, exterior perimeter, components, holes, and polygon area for 4,032 event sequences.
- Tested the day-5 acceleration hypothesis with development-only size thresholds and temporally separated calibration and held-out years.
- Added past-only perimeter-area, excess-perimeter, metabolic-rate, boundary-speed, fragmentation, and recent-phase predictors for later-area, peak-day, final-area, and death-day prediction.
- Added calibrated ridge, empirical-analog, and day-5 phase-mixture models with complete prediction, tuning, outcome, summary, QA-figure, and run-report outputs.
- Found that 62.4% of held-out top-decile fires peak after day 5, geometry improves later-area prediction, and precise death timing remains difficult, especially for the largest fires.

## 2026-09-28 - First-principles SI handoff report

- Added a reproducible 25-page PDF handoff for the Figure 4 two-thirds fire life-cycle model.
- Included the complete conditional proof, canonical parameter and stage summaries, machine-precision closure checks, five QA figures, and SI-ready Methods, Results, and qualification text.
- Added phase-stratified four-hour forecast statistics and a separate 1,000-run robustness and rank-sensitivity analysis.
- Embedded every proof-notebook code cell, the production model implementation, all report QA/statistical routines, and the defining automated tests.

## 2026-09-27 - Manuscript figure remakes and life-cycle prediction check

- Added reproducible Python remakes of the four current *Fire Critter* manuscript figures as high-resolution raster and vector assets.
- Reconciled the Figure 4 caption and artwork by combining four spatial fire-life stages with the measurable growth, perimeter, forcing, connectivity, and coupling trajectories.
- Added a 300-run synthetic robustness ensemble and past-only four-hour forecast comparison, with complete trajectory, forecast, summary, and manifest exports.
- Documented that the synthetic forecast result is phase-dependent and is not empirical wildfire validation.
- Replaced the independently shaped Figure 4 life-cycle signals with a coupled finite-fuel model built around `dA/dt = beta_0 C F eta A^(2/3)`, `P_a = k C A^(2/3)`, impedance matching, and mass-action connectivity dynamics.
- Added an executable proof notebook covering the geometric exponent, kinematic identity, cube-root transformation, matching-function optimum, invariant bounds, peak condition, numerical residuals, stage reconstruction, and ensemble prediction check.

## 2026-09-27 - Model-discrimination audit and prediction report

- Added a seven-page PDF report interpreting held-out FIRED final-area and duration prediction.
- Added a staged audit for reduced-law, empirical, flexible, weather, geometry, and conventional-model discrimination.
- Added a conventional-model comparison plan without fabricating event-matched ELMFIRE or Cell2Fire results.

## 2026-09-27 - FIRED grown-fire outcome validation

- Added temporally separated development, interval-calibration, and held-out validation for final area and duration predictions from early FIRED sequences.
- Added event-level descriptors of final size, duration, growth timing, peak daily growth, and burstiness.
- Added complete prediction, interval, summary, figure, and run-report outputs for 1,164 held-out events.

## Unreleased

- Added a leakage-resistant FIRED prediction workflow using real daily burned-area sequences, a 2001-2015 training period, held-out 2016-2020 tests, event-level bootstrap intervals, complete derived tables, and three diagnostic figures.
- Added the `fire_metabolism` scientific Python package as an executable mathematical companion to the *Fire Is Metabolic* Supplementary Information.
- Added 91 mathematical, numerical, construction, counterexample, worked-example, and evidence-boundary tests across the repository.
- Added a machine-readable claim ledger that distinguishes identities, conditional predictions, constructions, and empirical hypotheses.
- Added eight executable companion notebooks and `scripts/reproduce_si.py` with check-only mode, machine-readable results, and 15 labeled analytical/synthetic/hypothetical figures.
- Reproduced all seven hypothetical Section S19 worked examples at full precision without finding a numerical inconsistency.
- Added a reproducible builder for a single, complete computational Supplementary Information PDF containing the mathematical chain, figures, worked examples, counterexamples, claim ledger, and reproducibility record.
- Added development-quantile duration stratification and rolling day-10, day-14, and day-21 updates for FIRED life-cycle forecasts, showing that day-5 death and final-area prediction fails systematically for fires lasting 22 days or longer but improves strongly as later geometric state becomes available.
- Added state-conditioned discrete-time FIRED survival models with accelerating, declining, quiescent, and reactivated states, calibrated death-time distributions, conformal intervals, long-fire discrimination checks, and direct comparison with endpoint death regression.

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
