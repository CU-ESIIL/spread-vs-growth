# Supplementary Information Revision Map

Source reviewed: `supplementary-7.pdf`, 79 pages, Sections S1-S23. This is a
handoff map, not a rewrite.

## Section-level map

| SI section | Action | Mathematical reason and exact revision target |
| --- | --- | --- |
| S1 Proposition and physical meaning | **MODIFY** | State that the two-thirds relation motivates a conditional reduced model but does not identify metabolism, boundary dimension, or a universal trajectory. Point forward to the closed forcing and prospective transition test. |
| S2 Variables, units, reference scales | **MODIFY** | Retain units. Add `H`, `G`, `x`, `x0`, `tau`, `gamma`, `delta`, and `Psi`. Distinguish latent coherence `C` from measured graph connectivity and active fraction throughout. |
| S3 Dimensionality and history | **KEEP** | Its projection, resolution, and cumulative-footprint distinctions remain necessary and correct. |
| S4 Growth | **KEEP / MODIFY** | Keep amount-versus-rate and general growth law. Clarify that `M=A'` is area-growth rate inside the two-state model; chemical metabolic power requires the separate S11 bridge. |
| S5 Fuel consumption and energy release | **KEEP** | This is necessary for any chemical-metabolism claim. Cross-reference the fact that the two-state construction alone does not validate the energetic bridge. |
| S6 Thermodynamics and exhaust | **KEEP** | Retain as interpretation boundary, not part of the irreducible two-state ODE. |
| S7 Geometry | **KEEP / MODIFY** | Keep the dimensional ladder, finite-resolution qualifications, excess-perimeter diagnostic, and polygon counterexample. Add one explicit sentence that `2/3` is the weakest headline prediction and is not independent evidence for the later time exponents. |
| S8 Boundary kinematics | **KEEP** | Retain the regularity qualifications and source term. State that this is the sole named scientific axiom in the Lean kernel. |
| S9 Mapped perimeter-area closure | **MODIFY** | Separate mapped `P` from active `Pa` in notation and claims. Do not insert cumulative mapped perimeter directly into `Pa=kCA^(2/3)` without an independently tested mapping. |
| S10 Exact time dependence | **MODIFY** | Restrict affine cube-root area to constant composite forcing. Present `A~t^3` and `P~t^2` as late-time special-case consequences and explicitly note their algebraic dependence on `P~A^(2/3)`. |
| S11 Geometry-to-metabolism bridge | **KEEP / MOVE** | Keep as a separate energetic hypothesis after the two-state mathematical core. Do not use `M=A'` alone to claim chemical metabolic power. |
| S12 Candidate origins of four-thirds | **MOVE** | Keep as motivation and competing hypotheses, not as part of the authoritative equation chain. None uniquely selects the exponent. |
| S13 Transport matching | **MODIFY** | Retain the warnings about a chosen matching function. Add `CFeta=[2CF/(C+F)]^2`, symmetry, limiting quadratic suppression, bounds, and monotonicity. Explicitly distinguish “eta peaks at `C=F`” from the false claim that total forcing peaks there. |
| S14 Coupling and connectivity | **MODIFY** | Preserve the distinction between measured graph connectivity and latent coherence. Add the observability table and state that using mapped perimeter to define `C` and then validate growth is circular unless independently calibrated. |
| S15 Finite-fuel construction | **MODIFY SUBSTANTIALLY** | Present the canonical two-state system in `A,C`; treat `F,r,eta,M,Pa,v_eff` as derived. Add the closed forcing, dimensionless system, and `Psi=0` transition surface. Remove universal lifecycle implications. Correct interval-invariance and no-crossing statements by adding continuity and uniqueness/barrier assumptions. State that positive-state extinction is asymptotic. Require prospective `Amax`. |
| S16 Observation protocol | **MODIFY** | Add prefire delineation of `Amax`, active-perimeter measurement, and independent coherence construction. Explicitly prohibit final realized area as prospective `Amax`. Add uncertainty propagation for derivatives used in `Psi`. |
| S17 Forecasting | **KEEP / ADD** | Keep leakage-safe design. Add a held-out acceleration-sign and peak-crossing forecast based on `Psi`, compared with persistence, flexible trajectory, weather/fuel, and conventional spread baselines. |
| S18 Late growth and termination | **MODIFY** | Strengthen the existing warning that finite growth need not stop at finite time. State the new result: the unchanged smooth positive-state model predicts asymptotic extinction, so abrupt physical death diagnoses a threshold or omitted process. |
| S19 Testable propositions | **MODIFY SUBSTANTIALLY** | Replace an unranked list with the falsification hierarchy in `PREDICTION_HIERARCHY.md`. Add normalized forcing, coherence nullcline, and prospective transition tests above exponent fitting. Mark dependent consequences as such. |
| S20 Running example | **MOVE / MODIFY** | Retain as a conditional worked example, preferably after the authoritative core. Do not use its `2/3`, `t^3`, and `t^2` outputs as independent confirmations. Add one closed-forcing and one transition-balance calculation if inputs are independently specified. |
| S21 Reproducibility | **ADD** | Add the pinned Lean build, axiom audit, second-stage numerical sweep, and links to the final theory documents. Keep theorem, conditional theorem, numerical result, and empirical hypothesis labels distinct. |
| S22 Synthesis | **REPLACE MATHEMATICAL CHAIN** | Replace Eq. S87 as the sole “complete chain” with the two-state canonical core plus a separate observation/energetics layer. Make clear which equations generate trajectories and which only interpret or test them. |
| S23 Summary atlas | **ADD / MODIFY** | Add the proposed `C-F` forcing/nullcline/transition figure. Keep the current geometry and kinematics atlas panels as measurement cautions. |

## High-priority equation edits

### Eq. S56-S59: finite-fuel system

**MODIFY.** Replace the primary growth display with

```text
G(C,F) = [2CF/(C+F)]^2,
A' = beta0 G(C,F) A^(2/3),
C' = alpha C(1-C)F-mu C,
F = (Amax-A)/(Amax-A0).
```

Then present `r` and `eta` as an equivalent factorization, not additional
state variables.

**MODIFY.** Replace “the interval remains invariant because its derivative has
the correct boundary signs” with “the boundary signs support invariance when
combined with existence and forward uniqueness (or an equivalent barrier
theorem).”

**MODIFY.** Replace “area cannot pass `Amax` because `F=0` makes `A'=0`” with a
conditional barrier statement requiring a continuous solution and forward
uniqueness.

**ADD.** Define the transition surface `Psi=0` and state that a local maximum
requires a positive-to-negative crossing.

### Eq. S28-S30 and time-law language

**MODIFY.** Use “affine cube-root area under constant composite forcing” rather
than an unqualified cubic growth law. Use rigorous shifted-time or ratio-limit
language for `t^3` and `t^2`.

**ADD.** State that the exponent triplet contains only two independent
constraints.

### Eq. S51 matching

**KEEP** the algebra and warning that the function does not select a dimension.

**ADD.** The overall forcing is `G=CFeta`, whose partial derivatives are
positive. Therefore the matching-efficiency maximum at `C=F` is not a maximum
of total forcing.

### Eq. S60-S76 observation and prediction

**ADD.** Require `Amax` to be defined from information available at forecast
origin. Add state-closure residuals

```text
R_G = A'/A^(2/3) - beta0 G(C,F),
R_C = C'/C - alpha(1-C)F + mu,
```

and a held-out sign score for `sign(M')` versus `sign(Psi)`.

## Claims to flag wherever they occur

- **REMOVE or qualify:** `2/3` as identification of a unique geometry or mechanism.
- **REMOVE or qualify:** global `t^3` and `t^2` language outside constant forcing.
- **REMOVE:** universal recruitment-peak-decline language.
- **REMOVE:** finite-time death as a consequence of the smooth model.
- **REMOVE:** retrospective final area used as `Amax` in a forecast.
- **MODIFY:** mapped perimeter used as active perimeter without validation.
- **ADD:** area and perimeter do not identify individual latent factors.
- **REMOVE:** counting the three exponent relations as independent evidence.

## Material to preserve

The SI already contains strong safeguards that should remain: the distinction
between cumulative and active boundaries, resolution sensitivity, kinematic
source terms, the polygon and projection counterexamples, the warning that
matching does not select a dimension, leakage-safe forecasting, independent
power measurement, and modular failure interpretation. The revision should
tighten the finite-fuel synthesis around those safeguards, not discard them.
