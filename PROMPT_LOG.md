# Prompt Log

This file records substantive user prompts and the repository changes made in response. Keep entries concise, factual, and useful for reconstructing project intent.

## 2026-09-27

### Prompt

> Turn the mathematical Supplementary Information for "Fire Is Metabolic" into a rigorous, transparent, reproducible scientific Python package while preserving the distinction between identities, assumptions, conditional predictions, and empirical hypotheses.

### Response Summary

- Added the `src/fire_metabolism/` package covering geometry, kinematics, growth, energetics, residence time, scaling, forecasting, diagnostics, synthetic experiments, units, and the seven worked examples.
- Added exact tooth/notch polygon coordinates, symbolic residual checks, numerical ODE comparisons, dimensional checks, finite-speed and transport counterexamples, and leakage-resistant forecasting APIs.
- Added a machine-readable claim ledger, eight notebooks, a full reproduction script with check-only mode, and 15 figures explicitly labeled analytical, synthetic, or hypothetical.
- Added and ran 91 repository tests, reproduced all Section S19 target values, and found no mathematical or numerical inconsistency in the requested checks.
- Documented that no wildfire observations were downloaded and no empirical hypothesis was validated.

### Prompt

> can you give me a single pdf creating the entire si that I gave you?

### Response Summary

- Added `scripts/build_computational_si_pdf.py` to assemble the complete computational SI into one reproducible, paginated PDF.
- Included the scientific contract, equations, assumptions, 15 figures, seven worked examples, counterexamples, model-experiment framework, statistical API, claim ledger, and reproducibility appendices.
- Added PDF-generation dependencies and kept the rendered document outside git under `output/pdf/`.

### Prompt

> can you try some real prediction tests using sequences of real fires from fired?

### Response Summary

- Added a FIRED GeoPackage attribute reader and gap-free daily cumulative-area reconstruction without copying the 548 MB source into the repository.
- Added rolling one-, two-, and three-day forecasts for no growth, linear area, `sigma = 1/2`, `sigma = 2/3`, and an exponent selected using training years only.
- Defined a chronological 2001-2015 training and 2016-2020 held-out test split with event-balanced errors and whole-event bootstrap intervals.
- Retained 4,032 complete events and found that training selected `sigma = 0`; persistence was narrowly best at one day across all targets, while linear area was best at two and three days and on growth-only targets.
- Documented the official source, citations, format, access date, license uncertainty, and MODIS/FIRED interpretation limits.
- Added reproducible output tables, run metadata, and forecast-performance, exponent-selection, and observed-versus-predicted figures.

### Prompt

> how about some prediction validation. use the fired dataset to make some predictions and then test those predictions or make some descriptive statistics that end up describing the grown fire.

### Response Summary

- Added final-area and duration prediction from FIRED observations available through event days 3, 5, and 7.
- Separated model development (2001-2012), interval calibration (2013-2015), and held-out validation (2016-2020) to prevent temporal leakage.
- Compared no-future-growth, historical-median, and early-trajectory models; the early-trajectory model was best at every snapshot.
- Added 90% calibrated intervals and event-bootstrap uncertainty for point-error metrics.
- Added event-level and grouped descriptions of final area, duration, accumulation timing, peak growth, active-day fraction, and growth burstiness.

### Prompt

> Continue the FIRED prediction report, then audit and plan a rigorous model-discrimination experiment comparing reduced growth laws, empirical models, weather/geometry extensions, and future conventional spread models.

### Response Summary

- Built and visually verified a seven-page FIRED prediction validation PDF from machine-readable analysis outputs.
- Added `MODEL_DISCRIMINATION_AUDIT.md` covering the scientific contract, reusable code, leakage risks, common model schema, exact experiments, output/test contracts, computational cost, and decisions requiring review.
- Identified future-derived dominant land cover in the published ridge benchmark and future-conditioned cohort selection as interpretation and leakage risks that must remain explicit.
- Separated direct fixed-horizon reduced-law tests from final-area prediction, which requires an additional termination or outcome model.
- Added `CONVENTIONAL_MODEL_COMPARISON_PLAN.md` with a common adapter, input tiers, FIRED initialization questions, an ELMFIRE tutorial smoke test, and a development-only feasibility sequence.
- Stopped after Stage 1 without implementing or tuning new models against the 2016-2020 validation events.

## 2026-07-16

### Prompt

> i just started this repo from a template. I now need to rename and reasign everything to be for the new repo. The purpose of this repo is to compare spread rate and growth rate. I want to make figures for a talk and that involves bigger files and longer runs that I can do in a chat alone. Here is the current storyboard for the talk and we're going to try to animate much of this

### Response Summary

- Retargeted the repository from the starter template to `spread-vs-growth`.
- Updated README, MkDocs configuration, homepage, requirements, ignore rules, and changelog.
- Added project directories for source code, scripts, notebooks, data, outputs, and temporary files.
- Added storyboard and workflow documentation based on the ESA 2026 Fire Metabolism PDF.
- Removed stale template workflows and unused starter website assets.
- Verified the MkDocs site builds in strict mode.

### Prompt

> add an agents.md file and a prompt log

### Response Summary

- Retargeted the existing root `AGENTS.md` with project-specific guidance.
- Added this `PROMPT_LOG.md` file.
- Linked the prompt log from the README.

### Prompt

> i added two videos to the data folder. can you write a python script that puts both those videos in the same image side by side and cuts that into a new video? i want one video with the ink diffusion on one side and the slime mold or ameoba growing on the right.

### Response Summary

- Added `scripts/make_side_by_side_video.py` to stitch the ink diffusion video and slime-mold timelapse into one side-by-side MP4.
- Updated requirements with the video writer dependency.
- Documented the script in the scripts README and workflow docs.

### Prompt

> i see the files in the output folder but they won't open

### Response Summary

- Diagnosed the first render as a valid but nonstandard `1920x540` H.264 MP4.
- Updated the script defaults and writer settings to produce a standard `1920x1080` H.264 MP4 with player-friendly settings.

### Prompt

> now make a perimeter polygon around those at different stages of progress so we can measure the perimeter and area growth through time.

### Response Summary

- Added `scripts/measure_perimeter_growth.py` for stage sampling, segmentation, perimeter tracing, and area/perimeter measurement.
- Added `scikit-image` to requirements for contour tracing and morphology.
- Documented the measurement outputs in the scripts README and workflow docs.

### Prompt

> can you add a log area vs perimter graph for each.

### Response Summary

- Updated `scripts/measure_perimeter_growth.py` to write a two-panel log area-vs-perimeter graph for ink diffusion and slime mold.
- Documented the plot output in the scripts README and workflow docs.

### Prompt

> The attached pasted text file(s) contain the user's request. Read and act on that content.

### Response Summary

- Added a Tier-1 fire-model perimeter-area scaling workflow for exact ellipse, Huygens, level-set, and cellular mechanisms.
- Added shared geometry, metric, fitting, plotting, runner, and test modules under `src/fire_model_scaling/`.
- Added experiment configuration, reproducibility commands, generated metrics/fits/figures, and explicit actual-model status logs for ELMFIRE and Cell2Fire.

## 2026-07-17

### Prompt

> let's try running them for real

### Response Summary

- Cloned official ELMFIRE and Cell2Fire repositories into ignored `external/` checkouts.
- Built ELMFIRE natively on macOS far enough to produce `elmfire_perf_2025.1002`, then ran the official tutorial 01 constant-wind case successfully after local ignored-checkout fixes for macOS `sed` and Homebrew GDAL paths.
- Copied the real ELMFIRE tutorial outputs to `outputs/raw/elmfire_constant_wind/` and updated `actual_model_status.csv` to `run_success`.
- Attempted a native Cell2Fire C++ build; recorded failure caused by missing Boost headers and updated `actual_model_status.csv` to `build_failed_missing_boost`.
- Updated README, website workflow docs, changelog, and status-reporting code to reflect the real attempt outcomes.

### Prompt

> we want to add the model outputs to this figure in a way that matches style so hex bins would be good. can you generate a tone of outputs and try to create this plot. my expectation is that all the model outputs go along the 1/2 line.

### Response Summary

- Added `scripts/make_model_hexbin_plot.py` to generate a dense homogeneous/anisotropic model-output cloud and render a reference-style log-log hexbin plot.
- Wrote dense metrics to `outputs/metrics/model_hexbin_metrics.csv` and the figure to `outputs/figures/model_outputs_hexbin.png`, `.pdf`, and `.svg`.
- Corrected vector polygon metric scaling so non-unit `cell_size` values produce consistent area/perimeter units.
- Verified the combined dense model cloud fit is near the `1/2` line, with overall fitted slope approximately `0.51`.

### Prompt

> that is good but the variance is so low. what if we add more heterogeneity?

### Response Summary

- Extended `scripts/make_model_hexbin_plot.py` with explicit `--heterogeneity-levels` and `--output-name` options.
- Generated a higher-variance heterogeneous model cloud using heterogeneity strengths `0.25`, `0.5`, and `0.75`.
- Wrote the heterogeneous plot to `outputs/figures/model_outputs_hexbin_more_heterogeneity.png`, `.pdf`, and `.svg`, with metrics in `outputs/metrics/model_outputs_hexbin_more_heterogeneity_metrics.csv`.
- Measured an overall heterogeneous cloud slope of approximately `0.54`; the level-set emulator subset increased most strongly, to approximately `0.64`.

### Prompt

> can we pull out the level set into their own plot?

### Response Summary

- Added model filtering and optional input metrics support to `scripts/make_model_hexbin_plot.py`.
- Generated a level-set-only heterogeneous hexbin figure at `outputs/figures/level_set_hexbin_more_heterogeneity.png`, `.pdf`, and `.svg`.
- Verified the level-set-only filtered cloud has 7,920 valid outputs and fitted slope approximately `0.64`; subsets ranged from about `0.50` for homogeneous wind scenarios to about `0.76` for the strongest heterogeneity level.

### Prompt

> an now one without the level set included

### Response Summary

- Generated a heterogeneous hexbin figure excluding the level-set emulator at `outputs/figures/no_level_set_hexbin_more_heterogeneity.png`, `.pdf`, and `.svg`.
- Used the existing dense heterogeneous metrics and filtered to exact ellipse, Huygens emulator, and cellular emulator outputs.
- Verified the filtered cloud has 15,666 valid outputs and fitted slope approximately `0.51`, confirming the higher-slope behavior is primarily from the level-set emulator.

### Prompt

> can you give me the dataset for all those model runs organized so that I can plot the level set and the other models seperatly. i'm going to give this to a differnt agent to add to their graph and I need the dataset to be complete.

### Response Summary

- Added `scripts/export_model_run_dataset.py` to package the dense heterogeneous model-run outputs for handoff.
- Exported `outputs/datasets/model_hexbin_handoff/model_runs_all.csv`, `model_runs_level_set.csv`, and `model_runs_other_models.csv` with grouping fields, parsed heterogeneity, plot-valid flags, and explicit kilometer units.
- Added `model_fit_summary.csv`, `data_dictionary.csv`, `manifest.json`, `README.md`, and `model_hexbin_handoff_dataset.zip`.
- Verified the complete handoff contains 23,629 rows: 7,920 level-set rows and 15,709 other-model rows.

## 2026-07-20

### Prompt

> Create a reproducible Python animation of a grassland wildfire whose evolving burned-area footprint satisfies approximately P proportional to A^(2/3) over most of its growth trajectory.

### Response Summary

- Added `scripts/animate_grass_fire_two_thirds.py`, a deterministic calibration and rendering workflow for a shallow grassland fire animation.
- Generated `outputs/grass_fire_two_thirds/grass_fire_two_thirds_diagnostic.mp4` and `grass_fire_two_thirds_clean.mp4` as 1920 x 1080, 30 fps, 16-second MP4 files.
- Wrote `grass_fire_final_frame.png`, `perimeter_area_scaling.png`, `metrics.csv`, `accepted_parameters.json`, and an output README under `outputs/grass_fire_two_thirds/`.
- Verified the accepted contour-perimeter fit: `sigma=0.6882`, 95% CI `[0.6798, 0.6966]`, `R^2=0.9864`, 359 fitted frames, and a 20.84x fitted area range.

### Prompt

> can you give me this figure again without the 2/3 or 3/4 lines

### Response Summary

- Added `--hide-high-reference-lines` to `scripts/make_model_hexbin_plot.py`.
- Regenerated the no-level-set heterogeneous hexbin plot without the `2/3` or `3/4` reference lines.
- Wrote `outputs/figures/no_level_set_hexbin_half_fit_only.png`, `.pdf`, and `.svg`; the filtered model-cloud fit remains approximately `0.51`.

### Prompt

> now can you make an mp4 of the data appearing from left to right, starting with no data and ending with all the model data. This is just for the model data like the last still figure you made.

### Response Summary

- Added `scripts/animate_model_hexbin_reveal.py` to render the no-level-set heterogeneous model cloud as a left-to-right reveal animation.
- Wrote `outputs/animations/no_level_set_hexbin_reveal.mp4` as an 8-second, 30 fps, `1920 x 1080` H.264 MP4.
- Verified the animation uses 15,666 valid non-level-set outputs with fitted slope approximately `0.51`, and omits the `2/3` and `3/4` reference lines.

### Prompt

> I don't need to show it at 0, but it needs to try to intersect 00 so the rest of the line is in the correct spot

### Response Summary

- Corrected the red `1/2` reference line in the no-level-set hexbin still and reveal animation so it uses `P = sqrt(4*pi*A)`, which tends to `(0, 0)` in linear coordinates.
- Corrected the dotted model-fit line to use the fitted OLS intercept and slope instead of borrowing the same visual anchor as the reference line.
- Regenerated `outputs/figures/no_level_set_hexbin_half_fit_only.png`, `.pdf`, `.svg`, and `outputs/animations/no_level_set_hexbin_reveal.mp4`.

### Prompt

> the red line should be at the same place as the trend line but it's below it now

### Response Summary

- Repositioned the red `1/2` reference line to share the fitted model-cloud intercept with the dotted model trend line, so the two lines sit in the same visual location while retaining distinct exponents.
- Regenerated `outputs/figures/no_level_set_hexbin_half_fit_only.png`, `.pdf`, `.svg`, and `outputs/animations/no_level_set_hexbin_reveal.mp4`.
- Verified the final equations are `P = 4.107439 * A^0.5` for the red reference and `P = 4.107439 * A^0.506283` for the fitted trend.

### Prompt

> back to the grassland fire video. I actually wanted that video to be like the side by side red and blue animations but with less of a dome so people can visualize this in a grassland and a forest and a WUI

### Response Summary

- Added `scripts/animate_fire_contexts_explainer.py`, which reuses the accepted two-thirds fire-growth footprint and renders a flat perspective explainer across grassland, forest, and WUI contexts.
- Wrote `outputs/grass_fire_two_thirds/grass_forest_wui_growth_explainer.mp4` as a 15-second, 30 fps, `1920 x 1080` H.264 MP4.
- Wrote a final frame and metadata JSON beside the video, with display values scaled to kilometers for the talk graphic.

### Prompt

> back to the mp4. can you now make one with the blue line and red line but no data or model data?

### Response Summary

- Added `scripts/animate_reference_lines_only.py` to render a data-free log-log reference-line animation.
- Wrote `outputs/animations/reference_lines_red_blue_only.mp4` as a 6-second, 30 fps, `1920 x 1080` H.264 MP4.
- Included only the blue `P proportional to A^(2/3)` and red `P proportional to A^(1/2)` lines, with no hexbins, model points, or model-fit line.

### Prompt

> can you have the red line already in there and animate the blue line being drawn, you can make both lines thicker.

### Response Summary

- Updated `scripts/animate_reference_lines_only.py` so the red `1/2` reference line is fully present from the first frame.
- Increased both reference line widths and regenerated `outputs/animations/reference_lines_red_blue_only.mp4` with only the blue `2/3` line drawing on from left to right.

### Prompt

> can you give me this as a png with the blue line over it?

### Response Summary

- Added `scripts/add_two_thirds_line_to_image.py` to overlay a blue `P proportional to A^(2/3)` reference line onto an existing log-log event-hexbin PNG.
- Wrote `outputs/figures/event_hexbin_with_blue_two_thirds.png` using the provided pasted image as the source.

### Prompt

> that blue line has the correct slope but it's not intercepting 0,0, probably because log of 0 is nonsense so yo moved it. but it should do through 0,0 to line up with the data. also make the line thicker and more transparent cornflower blue.

### Response Summary

- Lowered the blue `2/3` overlay coefficient so the line enters from the lower-left plotting boundary and visually continues toward the linear-coordinate origin.
- Regenerated `outputs/figures/event_hexbin_with_blue_two_thirds.png` with a thicker, transparent cornflower-blue line.
- Updated `scripts/add_two_thirds_line_to_image.py` defaults to use the revised coefficient, width, and alpha.

### Prompt

> that looks the same

### Response Summary

- Further lowered the blue `2/3` overlay coefficient and wrote a distinct output file, `outputs/figures/event_hexbin_with_blue_two_thirds_origin_aligned.png`, to avoid stale image caching.
- Regenerated the overlay from the original no-line source image rather than from a screenshot that already contained the old blue line.

### Prompt

> here is the current version of the manuscript, will you please try to remake these figures from scratch but at large size and high resolution like they are now. notice the life and death of a fire figure that shows stages of growth and then declining growth. can you try to make those in python also? my goal would be to test that these are robust and predictive.

### Response Summary

- Added `src/fire_metabolism/manuscript_figures.py` and `scripts/remake_manuscript_figures.py` to regenerate four manuscript figures as 400-dpi PNG, vector PDF, and SVG assets.
- Rebuilt the life-and-death figure with four spatial stages and linked area, active-perimeter, growth-rate, forcing, connectivity, and edge-coupling trajectories.
- Added a 300-run perturbed synthetic ensemble, past-only four-hour forecasts, complete CSV exports, a manifest, and tests for monotonic area, ordered stages, determinism, and future leakage.
- Found phase-dependent internal predictive skill: cube-root area was best during acceleration, linear area near peak, and no-growth during decline; documented that this is not empirical wildfire validation.

### Prompt

> in figure 4 can you create all of those lines from first principles and get those results. first principles meaning our metabolic rate scaled to 2/3

### Response Summary

- Replaced Figure 4's separately prescribed life-cycle curves with a coupled reduced system whose metabolic rate is exactly `dA/dt = beta_0 C F eta A^(2/3)`.
- Derived active perimeter, effective velocity, fuel depletion, impedance matching, connectivity, fragmentation, coupling capacity, edge exponent, power, and cumulative energy from two integrated states: burned area and coherent connectivity.
- Added exact tests for the two-thirds closure and the kinematic identity `dA/dt = v_eff P_a`, then regenerated Figure 4, its complete trajectory CSV, and the dependent synthetic forecast validation.
- Documented that the system is a mechanistic closure with fitted parameters, not an ab initio combustion model or empirical validation.

### Prompt

> can you make that a full proof in the python notebook code we're making.

### Response Summary

- Added `notebooks/09_first_principles_fire_life_cycle.ipynb` with a complete executable derivation of the Figure 4 two-thirds metabolic life-cycle model.
- Proved the conditional `4/3` hull to `2/3` perimeter-area bridge, the boundary-kinematic growth law, cube-root linearization, impedance-matching optimum, connectivity invariance, finite-fuel bound, and metabolic-rate peak condition.
- Reproduced the Figure 4 stages and 300-run prediction table from the tested package implementation.
- Executed all ten code cells successfully; the two-thirds residual was exactly zero and the kinematic residual was approximately `4.3e-14`.

### Prompt

> now give me a full pdf summary that I can pass onto prism to add to the SI. tell me all the details and give me all the code chunks. also give me any nice summary statistics or qa plots that are helpful.

### Response Summary

- Added `scripts/build_first_principles_si_handoff_pdf.py`, a reproducible builder for a 25-page SI handoff report.
- Included the complete conditional derivation, evidence boundary, canonical parameters and stages, exact closure residuals, SI-ready Methods and Results language, and explicit empirical limitations.
- Added five QA figures covering the life-cycle trajectory, recovered two-thirds slope, floating-point closure residuals, phase-specific forecast error, 1,000-run outcome distributions, and parameter sensitivity.
- Embedded all notebook code cells, the production model implementation, QA/statistical routines, and defining automated tests in the report appendices.

### Prompt

> I want to work on the predictions. we have seperate data saying taht most of the biggest fires stop accelerating after 5 days. maybe we can test that expliciltly and calibrate accordingly if it makes sense to do so. keep in mind that fired has a lot of data so we should try to draw from that rather than impose things just because. anyway, let's try to use the life cycle models to help us get to where we can make really good predictions as judged by using part of the fired time series to predict later parts of the time series and try to predict model death precisely, all from our perimeter to area scaling relationships and metebolic and geometric mechanisms.

### Response Summary

- Extracted cumulative polygon geometry for all 4,032 eligible FIRED sequences and reconciled polygon area with FIRED attributes.
- Tested the day-5 acceleration hypothesis using a development-only top-decile size threshold and independent calibration and held-out periods.
- Added geometry/metabolic and empirical-analog predictors for later area, final area, peak-growth day, and last-growth day, plus a calibrated day-5 phase mixture.
- Found that 62.4% of held-out top-decile fires peak after day 5; geometry improves area forecasts, but day-5 death prediction remains imprecise at 4.04 days MAE overall and 7.92 days for the largest fires.

### Prompt

> what about the much longer fires?

### Response Summary

- Defined long-duration groups using last-growth-day quantiles estimated only from development years: days 17, 22, and 29.
- Added held-out duration-stratified outcome and prediction tables plus a three-panel long-fire failure-mode figure.
- Found that 93.8% of held-out fires lasting 22-28 days and 93.9% lasting at least 29 days peak after day 5.
- Found severe day-5 underprediction of death for the longest fires, while seven-day area forecasts remain substantially more accurate than final-area forecasts.
- Extended the held-out experiment through day 21; among fires lasting at least 22 days, death-day MAE improved from 13.13 days at day 5 to 4.60 days at day 21 and final-area error improved from 3.03x to 1.29x.
- Documented the resulting need for rolling survival or hazard forecasts that allow re-acceleration and incorporate time-varying forcing.

### Prompt

> yes, try the state survival model

### Response Summary

- Added ridge-regularized discrete-time terminal-transition hazards conditioned on past-only accelerating, declining, quiescent, and reactivated state proxies.
- Preserved the development, calibration, and held-out temporal partitions and compared state-only and geometry-plus-state hazards directly with the existing endpoint models.
- Added complete death-time distributions, calibration-selected hazard shifts, split-conformal 90% intervals, long-duration discrimination, and three QA figures.
- Found that the geometry-state hazard improves day-21 long-fire MAE and within-two-day accuracy but does not beat endpoint regression on day-5 MAE.
- Found that nominal day-5 interval coverage is correct overall but fails badly for the long-fire subgroup, confirming that early missing state information rather than endpoint loss alone drives the long-fire error.

### Prompt

> how about indicators for when the fire enters the persistent regime? if we separate out just the ones in that regime are they more predictable? ... does that help us predict the death phase at all? ... can we tell from the growth trajectories which fires were suppressed more quickly than natural course would have taken them?

### Response Summary

- Added held-out persistent-regime classifiers using past-only geometry, state, and damage features at days 3, 5, 7, 10, and 14.
- Found that geometry plus state reaches AUC 0.704 on day 5 and 0.801 on day 7; high-confidence precision increases through time while sensitivity remains low.
- Added persistent-only oracle death models and operational probability blends; knowing the regime retrospectively reduces day-5 persistent-fire death MAE from 13.13 to 6.33 days.
- Derived and tested accumulated growth-based damage variables, finding that they are mostly transformed area history and add almost no independent predictive value.
- Exported external-termination-like candidates for later data linkage while explicitly declining to infer suppression without suppression labels or a credible counterfactual.

### Prompt

> can you generate a detailed pdf report of all the prediction work we've done and tests we've run and results. make sure to contextualize the results so we can understand what is happening and how good they are or aren't.

### Response Summary

- Added `scripts/build_full_prediction_evidence_report.py` and generated a 26-page evidence report under `output/pdf/`.
- Consolidated all empirical prediction stages, lifecycle and long-fire diagnostics, state survival, persistence and damage tests, suppression-like residuals, and synthetic first-principles validation.
- Clearly separated held-out predictions, retrospective oracle diagnostics, and synthetic checks and stated what each result can and cannot support.
- Added an executive scorecard, interpretation guardrails, a theory-gap analysis, recommended next tests, and complete provenance and reproduction commands.
- Verified 113 tests and 10 subtests and visually inspected all 26 rendered pages.

### Prompt

> i think that difference is fuel restriction or suppression

### Response Summary

- Reframed the endpoint residual as a potential-to-realization gap: geometry and state describe a persistent growth course, while fuel, weather, barriers, and suppression may restrict realization.
- Kept causal attribution provisional because FIRED contains no suppression labels, fuel-connectivity counterfactual, or incident-resource history.

### Prompt

> give me a revised report that includes that perspective. you may need to add some more tests

### Response Summary

- Added `fired_realization.py` and `run_fired_realization_gap.py` to fit a development-only persistent-course area model and quantify held-out realization fractions.
- Found that 71 high-confidence early-ending fires realized a median 40.8% of their persistent-course forecast, versus 115.7% for 46 high-confidence true persistent fires; the bootstrap median-difference interval excluded zero.
- Added retrospective gradual, intermediate, and abrupt terminal-growth signatures. Abrupt endings were 36.6% among early-ending candidates versus 8.7% among true persistent controls, with odds ratio 6.07 and Fisher exact `p = 0.00093`.
- Revised the evidence report to 28 pages with new potential-versus-realized and terminal-signature sections and explicit fuel-restriction/suppression hypotheses.
- Added three focused tests, bringing the verified suite to 116 tests and 10 subtests, and visually inspected all 28 report pages.

### Prompt

> can you also try to address some of the 'what is missing' stuff and add that to the report?

### Response Summary

- Added daily gridMET extraction and a documented source record for vapor pressure deficit, wind, 100-hour fuel moisture, energy release component, and precipitation.
- Added held-out day-7 model comparisons for a newly burned-boundary active-front proxy, past weather, both additions, and an observed next-day-weather oracle diagnostic.
- Found a modest persistence-discrimination gain from weather, essentially unchanged final-area accuracy, and only a 0.62-day reduction in persistent death MAE even with observed next-day weather.
- Found no multiplicity-adjusted terminal-weather separation between gradual and abrupt early endings using daily centroid gridMET.
- Confirmed abrupt-ending enrichment across four observation-window definitions, reducing concern that the signal is an artifact of one terminal-window choice.
- Expanded the PDF report with a missing-process closure audit and explicit priorities for fuel connectivity, suppression linkage, fire-scale weather, and sensor-process modeling.

### Prompt

> Turn the mathematical argument in `supplementary-7.pdf` into a Lean 4 + Mathlib proof-testing project. Separate definitions, assumptions, identities, empirical premises, and stronger assumptions; do not silently strengthen claims; finish without `sorry`; and provide a claims audit, assumptions audit, counterexamples, and scientific summary without changing the manuscript or existing scientific code.

### Response Summary

- Added the pinned `FireProof/` Lean 4.19.0 + Mathlib 4.19.0 project with separate modules for each part of the mathematical chain.
- Proved the core conditional scaling, growth, active-boundary, fuel, matching, connectivity, metabolism, identifiability, and units results without `sorry` or `admit`.
- Kept the moving-boundary transport identity as one explicit custom axiom and verified its dependency boundary with `#print axioms`.
- Added claim-by-claim, assumptions, counterexample, and scientific-interpretation reports that expose where continuity, uniqueness, positivity, or empirical validation is additionally required.
- Verified the complete project with `lake build` and `bash scripts/audit.sh`; no manuscript or existing scientific implementation was modified.
