# Changelog

## 2026-10-09 - One-half normalization empirical and formal re-audit

- Inventoried and classified repository one-half results as population laws,
  fire-conditioned scaling, origin-anchored extrapolation, local-slope
  shrinkage, temporal area growth, or schematics.
- Re-ran the locked 4,032-fire geometry comparison with development-locked,
  calibration-locked, retrospective fire-specific, prospective history-only,
  and origin-anchored normalization treatments.
- Found that the population one-half law is worse than two-thirds on
  independent held-out geometry, that the development exponent near `0.595`
  is best, and that one-half receives a significantly larger gain from
  retrospective fire-specific intercept fitting.
- Quantified normalization drift, area-expansion leverage, long-trajectory
  discrimination, latent-constraint interactions, and synthetic controls;
  added complete CSV outputs and a six-panel PDF/SVG/PNG figure.
- Added a FireProof normalization audit and dependency map plus seven Lean
  checks for anchoring, candidate ratios, unrestricted-coefficient
  non-identification, and explicit one-half/two-thirds geometric coefficients.
- Left all existing core Lean theorem statements and manuscript/SI files
  unchanged.

## 2026-10-09 - Latent realization and one-half falsification tests

- Added the formal `M_real=B K A^(2/3)` extension, realized-growth bounds,
  `B*K` identifiability counterexample, bounded-future result, and conditional
  shock-restoration theorem in Lean.
- Added origin-safe FIRED potential-growth residuals for all 4,032 fires,
  prospective deficit-risk models, change-point, termination, OT-timing, and
  attractor-shock analyses.
- Found modest prospective deficit-risk skill from geometry, almost no early OT
  signal, and no long-horizon point-forecast gain from the latent-hazard mixture.
- Falsified the proposed explanation that deficits make one-half competitive:
  one-half remains better in near-potential held-out transitions and does not
  concentrate its advantage in the strongest deficits.
- Added the detectability matrix, formal audit, required data products, and
  publication PDF/SVG/high-resolution PNG figures.

## 2026-10-08 - Effective coupling and geometric-attractor validation

- Added an origin-safe effective-coupling pipeline for 4,032 FIRED fires and 54,002 event-days, with model hierarchy, recursive area forecasts, long-horizon and updating-origin checks, acceleration decomposition, and full machine-readable outputs.
- Found that mapped geometry improves short-horizon observable-coupling prediction and structured propagation modestly improves held-out area forecasts, while calibration does not uniquely select the `2/3` normalization.
- Added an adversarial geometric-attractor design and full validation with four local-slope estimators, whole-fire bootstrap inference, measurement-error, shuffled-time and random-walk nulls, within-fire separation, long-fire returns, observation robustness, and downstream coupling tests.
- Found weak negative within-fire slope feedback but rejected a universal `2/3` attractor because the free equilibrium is unstable, measurement error explains stronger apparent reversion, total perimeter reverses the sign, and flexible dynamics predict better.
- Added publication PDF/SVG/high-resolution PNG figures, scientific reports, design locks, reusable modules, smoke paths, and focused tests.

## 2026-10-08 - Empirical Fire Critter manuscript figures

- Added two publication figures that render the locked FIRED adversarial-validation outputs without refitting detection, forecast, or transition models.
- Figure 1 combines representative held-out perimeter-area trajectories, day-specific slope distributions, geometric and persistent detection frequencies, and observation-rule sensitivity.
- Figure 2 combines day-7 held-out area-forecast errors, paired geometry increments, full-geometry versus binary-indicator value, and prospective acceleration prediction.
- Added a deterministic median-evidence rule for selecting compatible, ambiguous, and inconsistent day-10 trajectories rather than choosing unusually favorable examples.
- Exported 600-dpi PNG and vector PDF/SVG assets, publication-ready captions, exact plotted source tables, and an input-checksum manifest under `output/manuscript/`.
- Added focused tests for input availability, locked numerical values, exact reference exponents, past-only trajectory extraction, and deterministic rendering.

## 2026-10-08 - Adversarial Fire Critter detection and prediction validation

- Added a leakage-audited validation pipeline reusing 4,032 cached FIRED event sequences, cumulative geometry, past weather, and the fixed development/calibration/held-out partitions.
- Added uncertainty-aware geometric detection with fixed `1/2` and `2/3` comparisons, persistence requirements, perimeter-rule and temporal-sampling sensitivity, and topology, size, duration, weather, and ecosystem diagnostics.
- Found that full origin-time mapped geometry significantly improves held-out area forecasts beyond equally informed recent-dynamics and flexible baselines, while the binary two-thirds detector adds little.
- Found that fixed two-thirds temporal growth loses to half-power and recent-linear forecasts at every tested horizon; calibration selects `sigma=0` throughout.
- Added paired held-out acceleration-sign and sign-changing peak-transition tests, probability calibration, whole-event uncertainty, and explicit false-alarm reporting.
- Confirmed that latent coherence, prospective reachable fuel, abrupt physical termination, energetic metabolism, and event-matched operational-model superiority remain unidentifiable or untested.
- Added synthetic counterexamples, six publication figures in PDF/SVG/PNG, machine-readable evidence classifications, four scientific validation reports, and an SI claim-by-claim handoff.
- Added five focused tests plus a deterministic smoke path and verified the full pipeline with 2,000 event-bootstrap replicates.

## 2026-10-08 - Authoritative fire-metabolism theory synthesis

- Reduced the finite-fuel construction to an irreducible two-state system for area and latent coherence, with fuel and matched forcing defined algebraically.
- Added the canonical forcing `G(C,F)=[2CF/(C+F)]^2`, its symmetry, bounds, limiting behavior, and formal partial derivative.
- Formalized the dimensionless transition surface with no explicit matching-derivative term and distinguished a stationary metabolic point from a local maximum.
- Separated generative equations from geometric motivation, boundary kinematics, observation equations, and the independent chemical-power bridge.
- Added `THEORY_CORE.md`, manuscript-ready claims, a ranked prediction and falsification hierarchy, a section-level SI revision map, and a ten-question final synthesis.
- Identified that matching efficiency peaks at `C=F` while total matched forcing does not, and that only `A` and `C` are necessary dynamic states.
- Rebuilt the full Lean project and retained exactly one named custom scientific axiom: the moving-boundary identity.

## 2026-10-08 - Second-stage adversarial prediction audit

- Extended `FireProof/` with formal peak-balance, matching-derivative, dimensionless-regime, structural non-identifiability, matching-symmetry, and competing-mechanism theorems.
- Proved that the closed matching factor is `CFeta=[2CF/(C+F)]^2`, providing a stronger state-closure prediction than the headline exponents.
- Proved that the cubic area, quadratic perimeter, and two-thirds perimeter-area laws are algebraically dependent and supplied a non-metabolic kinematic construction reproducing all three.
- Added a deterministic 750-run sweep of the unchanged dimensionless ODE: 312 monotone-decline trajectories, 412 interior global peaks, 203 early-connectivity-loss cases, and no multiple metabolic peaks on the tested grid.
- Found a numerical observational twin with area RMSE `9.39e-7` but connectivity RMSE `0.140`, demonstrating severe practical latent-state ambiguity.
- Added prediction, identifiability, failure-mode, empirical-test, and seven-question scientific summaries with explicit theorem/evidence labels.
- Identified asymptotic rather than finite-time extinction as a new model prediction and proposed a minimal held-out peak-balance test against conventional spread baselines.

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

- Added a locked 4,032-fire within-between geometric scaling analysis that separates population (`0.614`), between-fire (`0.646`), and within-fire (`0.594`) perimeter-area exponents with whole-fire bootstrap uncertainty.
- Added fire-specific and hierarchical random-slope estimates, flexible power-law and lifecycle tests, measurement-error, original-scale, temporal-thinning, and perimeter-definition sensitivities.
- Added calibrated synthetic manifold reconciliation, normalized-geometry state prediction, algorithmically selected held-out examples, publication figures, a formal Lean dependency audit, and a manuscript handoff without modifying the manuscript or SI.

- Added an integrated real-FIRED geometry and spatial-reorganization experiment with 9,035 transitions, area-matched dilation nulls, balanced and unbalanced transport, simpler spatial competitors, held-out future-coupling and long-horizon forecasts, and publication figures.
- Added abstract Lean modules proving only the nonnegativity, separating-distance, conditional prediction-set, and generic Lyapunov consequences of reorganization, plus counterexamples showing that R alone does not determine future growth or latent mechanism.
- Documented that geometric departure predicts R, R does not consistently predict restoration toward `2/3`, and geometry plus OT yields small held-out K gains from five days onward without solving long-range area or death prediction.

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
