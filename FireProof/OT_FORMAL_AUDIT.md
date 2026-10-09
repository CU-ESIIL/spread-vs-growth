# OT Formal Audit

## Scope

The formal extension starts from an abstract footprint type and an abstract
nonnegative distance. It does not import measure theory or claim that the
empirical implementation is exact Wasserstein distance. This keeps theorem
dependencies visible and allows a simpler spatial metric to instantiate the
same interface if it wins empirically.

## Model versions

| Version | Added structure | Newly available result |
| --- | --- | --- |
| Model 0 | Existing reduced growth law | `M = K A^(2/3)` consequences only |
| Model 1 | Footprint, simple-growth operator, nonnegative distance, R | `R >= 0`; no new prediction |
| Model 2 | Empirical R-indexed future-K interval | Strict narrowing of admissible K and growth intervals |
| Model 3 | Generic `sigma*`, deviation, linear restoration | Restoration sign and Lyapunov decrease under explicit lambda bounds |
| Model 4 | Model 2 plus Model 3 | Both theorem families; no coupling arrow follows automatically |

## Theorem dependency map

| Theorem | Pure math | Existing growth closure | R definition | R-to-K closure | Attractor closure | Empirically tested |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `reorganization_nonnegative` | yes | no | yes | no | no | distance nonnegativity only |
| `reorganization_zero_iff` | yes | no | yes | no | no | separating property assumed |
| `observed_R_strictly_narrows_unconstrained_K` | yes | no | no | yes | no | candidate closure partially supported |
| `coupling_interval_gives_growth_interval` | yes | yes | no | supplies bounds | no | conditional |
| `linear_step_restores` | yes | no | no | no | yes | fixed-center dynamics not supported |
| `linear_step_decreases_lyapunov` | yes | no | no | no | yes | fixed-center dynamics not supported |
| `same_R_different_future_growth` | counterexample | no | observational R | absent | no | establishes non-identification |
| `large_R_without_restoration` | counterexample | no | observational R | absent | absent | consistent with empirical failure |
| `R_does_not_identify_latent_C_F` | counterexample | no | observational R | absent | no | FIRED cannot test C and F separately |

## What R adds without a closure

Only an additional observed coordinate. The compiled counterexamples show:

- same area and R, different K;
- same area and K, different R;
- same R, different future growth;
- large R without geometric restoration; and
- geometric restoration with R equal to zero.

Consequently, inserting R into a state vector does not by itself constrain M,
future K, or future area.

## Minimal predictive closure

The weakest implemented closure is an R-indexed interval:

```text
K_future in [H_lower(R), H_upper(R)].
```

When the interval is finite, it is a proper subset of unconstrained real K.
For nonnegative `A^(2/3)`, multiplying the interval by the area factor yields
corresponding growth-rate bounds. Lean proves both statements. Lean does not
prove that the bounds are calibrated, contain future K, or are narrower than
bounds based on geometry alone.

## Generic attractor result

`FireProof.Attractor` is generic in `sigmaStar`. If a discrete step satisfies

```text
sigma_next = sigma - lambda (sigma - sigmaStar)
```

with `0 < lambda < 2` and the state is not already at equilibrium, squared
deviation decreases. This mathematics cannot select `1/2`, `2/3`, or any
other center. Selection is empirical, and the current FIRED audit does not
support a universal `2/3` center.

## Axiom audit

`lake build` and `scripts/audit.sh` pass with no `sorry` or `admit`. The new
results depend only on Mathlib's standard logical foundations. They introduce
no custom axiom. The existing moving-boundary identity remains the sole named
scientific axiom in the project and is not used by these OT theorems.
