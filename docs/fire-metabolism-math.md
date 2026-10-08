# Fire Metabolism Mathematical Companion

This repository now includes an executable companion to the mathematical Supplementary Information for *Fire Is Metabolic*. Its purpose is to verify identities, derivations, numerical solutions, explicit constructions, and hypothetical examples while preserving the boundary between mathematical verification and empirical validation.

Passing the package checks does **not** establish that wildfire has a `2/3` perimeter-area exponent or that wildfire is metabolic. Those remain empirical hypotheses requiring independent observations.

## Evidence Classes

| Class | Meaning in this package | Example |
| --- | --- | --- |
| Identity | True from definitions or conservation bookkeeping | `dA/dt = integral v_n ds` for a tracked regular advancing boundary |
| Conditional derivation | Follows after named closures are supplied | `dA/dt = beta A^sigma` |
| Construction | Exact property of explicit synthetic coordinates | Right-angle family with between-size slope `2/3` |
| Counterexample | Blocks a tempting inference | `sigma=1/2` with changing `kappa` can produce trajectory slope `2/3` |
| Empirical hypothesis | Requires observations not included here | A persistent wildfire `2/3` perimeter-area regime |

The machine-readable ledger is at `claims/fire_metabolism_claims.json`.

## Lean Formal Audit

The independent `FireProof/` project translates the smallest mathematical kernel of the SI into Lean 4 + Mathlib. It is an implication audit, not an empirical validation: supplied assumptions are checked against their stated consequences, while empirical premises remain visibly empirical.

```bash
cd FireProof
lake build
bash scripts/audit.sh
```

The build is pinned to Lean 4.19.0 and Mathlib 4.19.0. The project contains no `sorry` or `admit`. `FireProof.Kinematics.boundary_kinematic_identity` is intentionally declared as the single custom scientific axiom because a full geometric-measure transport theorem and its regularity conditions are outside this project's kernel.

The formal audit establishes the conditional algebra behind the `4/3 -> 2/3` scaling bridge, growth transformation, matching function, finite-fuel bookkeeping, connectivity equilibrium, and logarithmic derivative decompositions. It also proves a counterexample in which a changing coefficient combines with a `1/2` exponent to produce an observed `2/3` slope. Dynamic no-crossing and interval-invariance conclusions are therefore stated only with explicit continuity and forward-uniqueness or barrier assumptions.

See `FireProof/CLAIMS_AUDIT.md`, `FireProof/ASSUMPTIONS.md`, `FireProof/COUNTEREXAMPLES.md`, and `FireProof/SCIENTIFIC_SUMMARY.md` for the claim-level findings.

### Second-stage prediction audit

The second stage tests necessity, uniqueness, structural identifiability, and
mechanism discrimination rather than repeating the algebra audit. It proves the
exact metabolic peak balance, derives a three-group dimensionless system,
formalizes latent-product and matching symmetries, and shows that the three
headline power laws contain only two independent exponent constraints.

The unchanged closed system was also evaluated on a deterministic 750-case
dimensionless grid. The sweep is explicitly numerical: it finds monotone
decline, interior peaks, early connectivity loss, fuel-limited and
mismatch-limited trajectories, and near-identical area histories with different
latent connectivity. It does not prove peak uniqueness.

```bash
cd FireProof
../.venv/bin/python scripts/adversarial_lifecycle.py
```

See `FireProof/PREDICTIONS.md`, `FireProof/IDENTIFIABILITY.md`,
`FireProof/FAILURE_MODES.md`, `FireProof/EMPIRICAL_TESTS.md`, and
`FireProof/SECOND_STAGE_SUMMARY.md`.

### Authoritative synthesis

`FireProof/THEORY_CORE.md` reduces the construction to two dynamic states and
separates the generative ODE from its geometric, kinematic, observational, and
energetic interpretation. `FireProof/MANUSCRIPT_CLAIMS.md` provides calibrated
claim language, `FireProof/PREDICTION_HIERARCHY.md` ranks tests by mechanism
specificity, `FireProof/SI_REVISION_MAP.md` maps every SI section to a revision
action, and `FireProof/SYNTHESIS.md` answers the final scientific questions.

The synthesis adds one important formal distinction: matching efficiency is
maximized at `C=F`, but the complete forcing `CFeta` is monotone in each
positive state and saturates rather than peaking at equality.

## Run The Reproduction

```bash
PYTHONPATH=src python scripts/reproduce_si.py
```

The normal run performs symbolic checks, runs the complete test suite, reproduces all seven hypothetical Section S19 examples, generates 15 analytical/synthetic/hypothetical figures, and writes:

```text
outputs/si_reproduction/validation_report.json
outputs/si_reproduction/worked_examples.csv
outputs/si_reproduction/figures/
```

For checks without regenerating figures:

```bash
PYTHONPATH=src python scripts/reproduce_si.py --check-only
```

A failed mathematical or regression check exits nonzero.

## Complete PDF

Build the entire computational SI, including all equations, assumptions, figures, worked examples, counterexamples, claim statuses, and reproducibility appendices, as one paginated PDF:

```bash
PYTHONPATH=src python scripts/build_computational_si_pdf.py
```

The result is written to:

```text
output/pdf/fire_metabolism_computational_si.pdf
```

## Package Map

| Module | Responsibility |
| --- | --- |
| `geometry.py` | Dimensional ladder, ellipses, box counting, exact tooth/notch polygons, connectivity |
| `kinematics.py` | Boundary integral, active subset, untracked source, residual diagnostic |
| `growth.py` | Analytic laws, numerical comparisons, acceleration, source terms, finite-speed bounds, termination |
| `energetics.py` | Front-associated consumption, flux-weighted energy, residual power, conditional power scaling |
| `residence.py` | Cohort convolution and exponential residence-time example |
| `scaling.py` | Normalized closures, exponent bridge, excess perimeter, percolation and transport counterexamples, estimation APIs |
| `forecasting.py` | Calibration/forecast separation and nonlinear back-transform uncertainty |
| `synthetic.py` | Staged/factorial spatial-model design and synthetic surface distinctions |
| `units.py` | Dimensional bookkeeping |
| `diagnostics.py` | SymPy residual checks and claim-ledger validation |
| `worked_examples.py` | Full-precision Section S19 calculations |

## Scientific Boundaries

- The mapped perimeter relation does not determine active-boundary fraction.
- Active fraction does not determine normal velocity.
- Geometry does not determine chemical power without fuel and residence-time assumptions.
- A between-size exponent is not automatically a within-boundary fractal dimension.
- A successful algebraic reproduction is not empirical validation.
- The reproduction layer downloads no wildfire observations.

The eight notebooks in `notebooks/01_...` through `08_...` expose the tested APIs for exploration without duplicating the mathematical implementation.
