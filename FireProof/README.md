# FireProof

`FireProof` is a Lean 4 + Mathlib adversarial formalization of the mathematical kernel in the *Fire Is Metabolic* Supplementary Information. It tests internal implication only:

```text
stated assumptions -> mathematical consequence
```

It does not prove that real wildfire satisfies those assumptions.

## Toolchain

- Lean 4.19.0
- Mathlib v4.19.0

Both versions are pinned by `lean-toolchain`, `lakefile.toml`, and `lake-manifest.json`.

## Build

```bash
cd FireProof
lake update
lake exe cache get
lake build
bash scripts/audit.sh
```

On macOS systems where the downloaded native cache helper is rejected by the dynamic loader, the equivalent interpreter command is:

```bash
lake env lean --run .lake/packages/mathlib/Cache/Main.lean get
```

## Module map

| Module | Scope |
| --- | --- |
| `Assumptions.lean` | Explicit proportionality, empirical-premise marker, and barrier/uniqueness predicates |
| `Scaling.lean` | Shared-size elimination, explicit coefficient, and `4/3 -> 2/3` |
| `Growth.lean` | Constant-beta transformed solution and rigorous cubic/quadratic ratio limits |
| `Kinematics.lean` | Named moving-boundary axiom and proved coarse-grained reductions |
| `ActiveBoundary.lean` | Active-boundary substitution and exact cube-root cancellation |
| `Fuel.lean` | Remaining-fuel bounds, derivative, and no-crossing theorem with explicit barrier assumptions |
| `Matching.lean` | Matching identity, positivity, unit bound, and unique global maximum |
| `Connectivity.lean` | Equilibrium algebra, threshold, boundary signs, and conditional interval invariance |
| `Metabolism.lean` | Derived relative/logarithmic derivative decompositions |
| `Identifiability.lean` | Local-slope formula and the formal `1/2 + 1/6 = 2/3` counterexample |
| `Units.lean` | Separate type-safe dimensional bookkeeping layer |
| `Lifecycle.lean` | Exact peak balance, sign logic, and lifecycle counterexamples |
| `Dimensionless.lean` | Canonical dimensionless fields and analytic connectivity boundaries |
| `MechanismTests.lean` | Observation-preserving rescalings, matching symmetry, and redundant headline laws |
| `Audit.lean` | Machine-readable status vocabulary and core claim records |

## Proof policy

- Claims marked `PROVED` contain no `sorry` or `admit`.
- `boundary_kinematic_identity` is an intentional, named axiom. The required geometric-measure/transport assumptions are documented rather than hidden.
- ODE invariance is not inferred from boundary signs alone.
- Empirical claims are recorded as empirical; no Lean theorem promotes them to facts about wildfire.

The human-readable findings are in:

- `CLAIMS_AUDIT.md`
- `ASSUMPTIONS.md`
- `COUNTEREXAMPLES.md`
- `SCIENTIFIC_SUMMARY.md`
- `PREDICTIONS.md`
- `IDENTIFIABILITY.md`
- `FAILURE_MODES.md`
- `EMPIRICAL_TESTS.md`
- `SECOND_STAGE_SUMMARY.md`
- `THEORY_CORE.md`
- `MANUSCRIPT_CLAIMS.md`
- `PREDICTION_HIERARCHY.md`
- `SI_REVISION_MAP.md`
- `SYNTHESIS.md`

Run the deterministic numerical stress test with the repository environment:

```bash
../.venv/bin/python scripts/adversarial_lifecycle.py
```

It writes a 750-run table and JSON summary under `results/`. These outputs are
explicitly labeled numerical results and are not used as Lean proofs.

No manuscript or existing scientific implementation was modified as part of the formal audit.
