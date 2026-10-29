# NSF X-Labs RFI Vetting

## Executive verdict

The RFI has a strong X-Labs-shaped idea: build a shared measurement and
prospective-validation platform around a scientific question that no single
discipline can answer. The empirical case is also stronger than the current
draft says. Mapped whole-fire geometry improves held-out future-area and
acceleration forecasts in the locked FIRED cohort.

The current version nevertheless tries to validate too many things with one
100-incident demonstration. It combines state reconstruction, model
comparison, metabolic mechanism, suppression attribution, five-regime
generalization, and operational forecasting. Those are linked research
programs, not one adequately powered experiment. The proposal will be more
credible if it makes one claim primary:

> An observable whole-fire state adds prospective predictive information
> beyond matched local-front, environmental, and area-history baselines.

Metabolic closure should be a mechanistic secondary hypothesis tested in
controlled burns. Chemical-energy accounting and suppression attribution
should be staged extensions, not dependencies of the minimum viable platform.

## What was verified

### External claims

| Draft claim | Audit result | Recommended treatment |
| --- | --- | --- |
| The 1972 Rothermel model predicts local surface-fire spread rate. | Verified. The USDA record describes a mathematical model for rate of spread and intensity. | Keep, but do not imply that all later fire models are identical to the original model. |
| Operational spread systems propagate a fire front. | Verified for the canonical tradition. FARSITE calculates one-dimensional spread at vertices of a two-dimensional front and propagates it with Huygens' principle. | Say the dominant operational tradition is local-front propagation, not that every traditional model necessarily predicts the same aggregate exponent. |
| The United States had 77,850 fires and 5,131,474 burned acres in 2025. | Verified in the NIFC 2025 annual report. The report also lists 18,385 structures destroyed, including 12,773 residences. | Keep with the NIFC citation and note that county-level reporting is incomplete in that report. |
| Fast fires are a small fraction of fires but dominate burned area and structure loss. | Verified. Balch et al. analyzed 60,012 fires; 1,616 fires exceeding 1,620 ha in one day were 2.7% of fires, accounted for 60.1% of burned area, and were associated with 89% of structures damaged or destroyed. | Replace loose wording with the exact threshold and population. Do not generalize this result to every fire inventory. |
| The RFI aligns with NSF X-Labs. | Verified. NSF emphasizes full-time interdisciplinary teams, foundational platform technology, operational autonomy, milestone-based funding, and experimental validation. | Make the platform and milestone structure more explicit throughout the response. |

Primary sources:

- [NSF X-Labs](https://www.nsf.gov/funding/initiatives/nsf-x-labs)
- [NIFC 2025 annual report](https://www.nifc.gov/sites/default/files/NICC/2-Predictive%20Services/Intelligence/Annual%20Reports/2025/annual_report_2025_0.pdf)
- [Balch et al. 2024, *Science*](https://eco-integrityalliance.org/wp-content/uploads/2024/10/balch-et-al-2024-fastest-growing-and-most-destructive-fires.pdf)
- [Rothermel 1972 USDA record](https://research.fs.usda.gov/treesearch/32533)
- [USDA Rothermel 50-year retrospective](https://research.fs.usda.gov/firelab/projects/rothermelfirespread)
- [FARSITE technical report](https://www.fs.usda.gov/rm/pubs/rmrs_rp004.pdf)

### Repository claims

The draft's empirical values were checked against locked repository outputs.

| Quantity | Locked result | Interpretation |
| --- | ---: | --- |
| FIRED fires | 4,032 | Locked cohort across development, calibration, and held-out years. |
| Held-out fires | 1,164 | Independent test years, 2016-2020. |
| All-fire pooled exponent | 0.614, 95% CI 0.610-0.617 | Population mixture of between- and within-fire variation. |
| All-fire within-fire exponent | 0.594, 95% CI 0.592-0.597 | Average longitudinal mapped trajectory. |
| All-fire between-fire exponent | 0.646, 95% CI 0.639-0.652 | Comparison among fires of different characteristic size. |
| Held-out pooled exponent | 0.613, 95% CI 0.608-0.619 | Reproduces the pooled result. |
| Held-out within-fire exponent | 0.595, 95% CI 0.590-0.600 | Reproduces longitudinal scaling. |
| Held-out between-fire exponent | 0.643, 95% CI 0.631-0.654 | Near two-thirds, but excludes exact two-thirds at 95%. |

These are different estimands, not conflicting estimates. Two-thirds is most
defensible as an approximate between-fire population geometry. It is not the
average temporal growth law of an individual mapped fire, and a fixed
two-thirds temporal forecast performs poorly. Use those distinctions every
time the exponent appears.

The older 237,235-event plot with a slope near 0.66 cannot currently be fully
regenerated from a preserved source table and exact analysis script. It can be
shown as historical context, but it should not carry a proposal claim until
its data lineage is restored. The locked 4,032-fire analysis is the auditable
evidence base.

## New quantitative results

### Future-area prediction

All values below are held out by fire year and scored with mean absolute log
error. Exponentiating the score gives a typical multiplicative error factor.

| Horizon | Area dynamics | Perimeter | Full geometry | Geometry skill vs dynamics |
| ---: | ---: | ---: | ---: | ---: |
| 1 day | 0.298 | 0.292 | 0.276 | 7.4% |
| 3 days | 0.444 | 0.423 | 0.385 | 13.4% |
| 5 days | 0.496 | 0.473 | 0.426 | 14.2% |
| 7 days | 0.525 | 0.504 | 0.455 | 13.3% |
| 14 days | 0.574 | 0.558 | 0.509 | 11.3% |
| 42 days | 0.608 | 0.593 | 0.544 | 10.5% |

At seven days, the typical error factors are 1.69 for dynamics, 1.65 for raw
perimeter, and 1.58 for full geometry. The paired geometry improvement is
`-0.070` log-area units versus dynamics and `-0.049` versus perimeter. Both
locked whole-fire bootstrap intervals exclude zero.

This supports a precise claim: multivariate mapped geometry adds reproducible
forecast information. It does **not** show that a two-thirds exponent itself is
the predictive ingredient; fixed normalizations become equivalent after area
and recent area change are included.

### Transition prediction

At day 7, predicting acceleration over the next three days:

- full geometry balanced accuracy: `0.790`;
- area-plus-dynamics balanced accuracy: `0.692`;
- paired gain: `0.098`, 95% CI `0.063-0.134`;
- Brier score: `0.146` versus `0.193`, a 24.3% relative reduction;
- held-out fires with an evaluable transition: `782`.

For a peak in the next three days, geometry reaches balanced accuracy `0.791`,
but precision is only `0.224`. This is useful discrimination, not a sufficiently
reliable operational alarm. The RFI should lead with acceleration, and report
peak prediction as a harder secondary outcome.

### Prospective sample size

Using event-averaged paired loss differences from the held-out cohort and a
two-sided normal approximation:

\[
n \approx \left(\frac{z_{0.975}+z_{\mathrm{power}}}{|\bar d|/s_d}\right)^2.
\]

| Primary comparison | 80% power | 90% power |
| --- | ---: | ---: |
| Seven-day geometry vs area dynamics | 45 fires | 60 fires |
| Seven-day geometry vs raw perimeter | 78 fires | 105 fires |
| One-day geometry vs raw perimeter | 151 fires | 202 fires |

These are planning approximations, not a preregistered power analysis. They
assume retrospective effects and event-level variance transfer to a new
prospective system. Repeated forecast origins within one fire do not replace
independent fires.

The draft's 100 incidents are roughly adequate for one pooled seven-day
geometry-versus-perimeter test. They are not adequate for separate claims in
five regimes. With 20 fires per regime, an observed 80% coverage rate has an
approximate 95% binomial margin of error of plus or minus 17.5 percentage
points; with 100 pooled fires it is still plus or minus 7.8 points.

### Rare outcomes

| Outcome | Observed prevalence | Expected positives in 100 fires | Per regime if split five ways |
| --- | ---: | ---: | ---: |
| Major three-day realization deficit | 5.6% | 5.6 | 1.1 |
| Peak transition in next three days | 6.3% | 6.3 | 1.3 |
| Duration at least 22 days | 12.5% | 12.5 | 2.5 |
| Duration at least 29 days | 4.2% | 4.2 | 0.8 |

No rare-event detector, extreme-duration model, or regime-specific
calibration claim should use the same 100-incident finish line. Either expand
the remote-sensing benchmark to at least 300 incidents, pool regimes for the
primary endpoint, or define rare outcomes as exploratory.

## Architecture audit

### Recommended platform

Keep **Wildfire State Observatory** as the platform name. Treat **Whole-Fire
State and Prediction** as the scientific program. Avoid carrying two equal
brands, because the current title and platform name make the proposal sound
like separate projects.

Organize the observatory into three linked tracks:

1. **Measurement and reference track.** Fuse airborne, satellite, thermal,
   meteorological, and incident data into probabilistic active-boundary,
   newly burned area, fuel-consumption, and radiative-power products with
   explicit uncertainty and latency.
2. **Prospective forecast testbed.** Issue timestamped forecasts from matched
   local-front, area-history, whole-fire-state, and hybrid models using the
   same information cutoff. Score them independently and preserve every
   forecast, input, model version, and exclusion.
3. **Mechanism track.** Use controlled burns to test whether reachable fuel,
   consumption, energy release, and geometry close a metabolic balance. This
   is where the strongest causal claims belong.

This architecture makes the platform valuable even if the metabolic mechanism
is partly falsified. It also prevents a difficult chemical-energy measurement
from blocking the predictive benchmark.

### Nested evidence tiers

- **Tier A: synchronization.** Five to ten instrumented prescribed burns to
  resolve timing, co-registration, reference-product definitions, and data
  latency. These establish feasibility, not ecological generality.
- **Tier B: mechanism and transfer.** Roughly 20-30 intensively observed burns
  and wildfires across two or three prespecified regimes. Test repeatability,
  transfer, and energetic closure.
- **Tier C: prospective benchmark.** At least 100 independent incidents for
  the pooled seven-day primary comparison; target 300 or more if the project
  promises regime calibration, rare transitions, or extreme-fire endpoints.

Define regimes before data collection. Useful axes are fuel structure
(grass/shrub/forest), topographic complexity, wind versus plume dominance, and
prescribed versus wildfire context. Five thin, vaguely named regimes are less
informative than two or three primary regimes plus a held-out transfer test.

### State definition

Do not ask whether a state “exists.” Define the testable question as whether a
low-dimensional, observable whole-fire state adds calibrated predictive and
mechanistic information beyond matched alternatives.

Define growth potential as a conditional forecast distribution given current
geometry, recent growth, reachable fuel, and specified forcing. Do not call it
an intrinsic or counterfactual maximum until fuel and suppression are
measured. FIRED trajectories alone can detect deviations from expected growth,
but cannot identify whether fuel, weather, barriers, suppression, or mapping
caused them.

### Reference observations

A wildfire does not present a perfectly observed line. Use a probabilistic
active-boundary field and separate it from cumulative mapped perimeter. Call
the fused products reference observations rather than ground truth. Each
product should include uncertainty, spatial support, observation time, and
latency.

### Primary outcomes

For state reconstruction, preregister boundary-probability Brier score and
reliability, localization error, motion-vector error, new-area intersection
over union, fuel-consumption bias, and product latency.

For forecasting, preregister spatial Brier score, continuous ranked
probability score, area log error, interval coverage and width, and
event-weighted paired differences. Resample whole fires, not individual daily
rows. Report performance by lead time and a small number of prespecified
regimes.

## Claims that need correction

### Q3: historical framing

The critique should be forceful but exact. The repository itself contains
heterogeneous level-set simulations with exponents near two-thirds, so “all
traditional models predict one-half” is false. A defensible statement is:

> The dominant operational tradition decomposes a fire into local front
> segments whose spread rates are propagated through space. Under smooth,
> self-similar expansion this construction yields perimeter proportional to
> area to the one-half power, whereas satellite fire populations show a
> between-fire exponent near 0.65. Heterogeneous front models can also produce
> exponents near two-thirds, so the decisive test is not the exponent alone but
> whether an observable whole-fire state improves matched prospective
> prediction.

This preserves the paradigm challenge without asserting a result the project
has already falsified.

### Q11: evidence

Add the held-out acceleration result and an intuitive error translation. Keep
the estimator distinctions. Suggested response:

> In a locked cohort of 4,032 FIRED events, the between-fire
> perimeter-area exponent is 0.646 (95% CI 0.639-0.652), while the within-fire
> exponent is 0.594 (0.592-0.597); the same distinction reproduces in 1,164
> held-out fires. Thus near-two-thirds describes population geometry better
> than an individual temporal law. Full mapped geometry nevertheless improves
> held-out future-area prediction: at seven days, mean absolute log error is
> 0.455 versus 0.525 for area dynamics, a 13.3% gain and typical error factor
> of 1.58 versus 1.69. At day 7, geometry predicts acceleration over the next
> three days with balanced accuracy 0.790 versus 0.692; the paired gain is
> 0.098 (95% CI 0.063-0.134), and Brier score falls 24.3%. Fixed exponents alone
> are not predictive after conditioning on area and recent growth. These are
> retrospective satellite results that motivate, but do not replace, a
> timestamped prospective test.

### Q12: resources

Replace one undifferentiated campaign with the three evidence tiers. State
that the principal infrastructure is not only sensors: it is the synchronized
reference-product pipeline, immutable forecast registry, matched-input model
runner, and independent scoring service.

### Q13: finish line

The current six-hour, 20% spatial-Brier target is not supported by the daily
FIRED area experiment. Keep it only as a stretch target to be calibrated in
Tier A. Suggested response:

> By 2031 the Wildfire State Observatory will deliver uncertainty-qualified
> active-boundary, newly burned area, consumption, and forcing products plus
> an immutable prospective forecast registry. Its primary demonstration will
> compare whole-fire-state, local-front, area-history, and hybrid models on at
> least 100 independent incidents, using matched information cutoffs and a
> preregistered seven-day paired endpoint. Retrospective effect sizes imply
> about 78 incidents for 80% power against a perimeter baseline and 105 for
> 90%; the final target will be re-estimated from Tier-A pilot variance. A
> larger 300+ incident benchmark will support regime calibration and rare-event
> analyses. Six-hour spatial forecasts will be scored with Brier score, CRPS,
> calibration, coverage, sharpness, and latency; minimum useful margins will
> be locked after pilot data, not inferred from daily area errors.

### Q15: limitations

The statement that adversarial-validation artifacts are absent is incorrect.
Complete row-level predictions, whole-fire bootstrap distributions, design
locks, reports, and provenance already exist under
`outputs/final_state_audit/` and `outputs/adversarial_validation/`. The scaling
values also reconcile by estimand and data partition. Suggested response:

> The strongest evidence remains retrospective and satellite-derived. The
> locked audit includes row-level held-out predictions, whole-fire bootstrap
> distributions, design records, and provenance, but it does not provide
> prospective timestamps, high-cadence active-boundary observations, fuel
> consumption, radiative energy closure, or suppression exposure. Pooled,
> within-fire, and between-fire exponents differ because they answer different
> questions; exact two-thirds is not supported as a universal temporal law.
> Geometry improves prediction, but FIRED cannot identify whether a growth
> deficit was caused by fuel, weather, barriers, suppression, or observation.
> Operational front-model comparisons are not yet matched on inputs and
> information cutoffs. The proposed observatory is designed to close those
> measurement and prospective-validation gaps.

### Q19: transition pathways

The current response is too generic for a translation-oriented program. Name
concrete pathways: an agency-ready state-estimation interface, a sensor
calibration and reference-product service, an open forecast benchmark and
model certification harness, and integration contracts for operational and
commercial forecast providers. Do not promise decision safety or suppression
benefit before prospective validation.

### Q21 and Q22: optional fields

The official RFI permits respondents to answer any or all questions. If no
facility commitment or in-kind resource is confirmed, omission is stronger
than “not yet confirmed.” Use the recovered characters in Q11-Q15, where added
specificity changes credibility.

## Portal and presentation audit

All 28 extracted responses are under the 1,300-character portal limit. The
longest is 1,114 characters, the median is 710.5, and the draft leaves 15,751
characters unused in total. Q14, Q21, and Q22 are especially sparse. This is
not a reason to fill every field: the RFI explicitly values depth over shallow
coverage. Spend characters on hypotheses, estimands, power, milestones, and
translation paths.

The RFI would benefit from a single repeated logic chain:

1. **Problem:** local spread rates do not fully specify whole-fire growth.
2. **Observation:** population geometry and within-fire dynamics are distinct.
3. **Evidence:** multivariate geometry adds held-out predictive information.
4. **Unknown:** energetic closure, active boundary, forcing, and intervention
   are not observed together.
5. **Platform:** synchronize those observations and run timestamped matched
   forecasts.
6. **Decision:** retain, revise, or reject whole-fire mechanisms by prospective
   score and controlled-burn closure.

## Reproducibility

Run the proposal audit from the repository root:

```bash
../cubedynamics/.venv/bin/python scripts/audit_xlabs_rfi.py \
  --rfi-pdf /Users/tuff/Downloads/nsf_xlabs_rfi-9.pdf
```

The script writes character counts, scaling reconciliation, held-out proposal
metrics, paired sample-size approximations, transition summaries, rare-event
design tables, and a JSON synopsis under `outputs/xlabs_rfi_audit/`. Generated
outputs remain ignored; source code and this interpretation are versioned.

## Evidence boundary

- The sample-size calculation is a planning approximation, not a replacement
  for a simulation-based analysis using prospective pilot data.
- The FIRED product is a mapped-area sequence, not a direct observation of the
  active fire front, combustion rate, chemical energy, suppression, or
  reachable fuel.
- The current model comparison is empirical and retrospective. It is not yet a
  fair head-to-head test against an operational implementation supplied with
  identical real-time inputs.
- Scaling exponents describe statistical geometry and do not, by themselves,
  identify a metabolic mechanism.
- The platform remains scientifically valuable if it falsifies the strongest
  metabolic claim, because synchronized reference observations and prospective
  scoring are missing infrastructure for the entire field.
