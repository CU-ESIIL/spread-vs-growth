# Assumptions Audit

## Algebraic kernel

| Assumption | Where it enters | Why it is necessary |
| --- | --- | --- |
| `A, P, L, cA, cP > 0` | Scaling | Real logarithms and fractional powers represent physical positive quantities only on this domain. |
| `DA != 0` | Scaling elimination | Dividing by the area exponent is otherwise undefined; a zero area exponent does not determine length. |
| Shared characteristic size `L` | Scaling elimination | Without one common size variable, eliminating `L` is invalid. |
| Stable multiplicative coefficients | Fixed power-law interpretation | Drift in `cA`, `cP`, or `kappa` changes the observed log-log slope. |
| Nonzero denominators | Fuel, matching, equilibria | `Amax-A0`, `1+r`, `alpha`, and `alpha F` must not vanish where division is used. |

## Calculus kernel

| Assumption | Where it enters | Why it is necessary |
| --- | --- | --- |
| `A(t) > 0` | Fractional powers and transformed growth | The real-power derivative is single-valued and smooth there; relative derivatives also divide by `A`. |
| Differentiability on the forecast interval | Growth solution | The ODE must hold pointwise strongly enough to apply the mean-value uniqueness theorem for the transformed state. |
| Fixed `sigma` | Growth linearization | If `sigma` varies, differentiating `A^(1-sigma)` produces an additional `sigma' log A` term. |
| Constant `beta` | Affine transformed solution | Time-varying `beta` requires an integral; endpoint beta is insufficient. |
| Strictly positive `C`, `F`, and `eta` | Relative derivative of `M` | The displayed decomposition divides by all three states and by `M`. |
| Nonzero `beta0` and `k` | Relative derivative of `M` and `Pa` | The ratios are undefined when the corresponding quantity is zero. |

## Geometry and ODEs

| Assumption | Where it enters | Why it is necessary |
| --- | --- | --- |
| Regular moving boundary and a valid transport theorem | Boundary kinematics | Mathlib does not supply the full shape-derivative/GMT result used by the SI. It is the sole named scientific axiom. |
| No double-counted collisions or unresolved jumps | Boundary kinematics | A simple boundary integral otherwise fails to account for set union and discrete recruitment. |
| Continuity/intermediate-value crossing | Fuel ceiling and connectivity interval | A path cannot be ruled out from jumping across a boundary without attaining it. |
| Existence and forward uniqueness, typically from local Lipschitz regularity | Fuel ceiling and connectivity interval | A vector field that vanishes or points inward at a boundary does not by itself force every solution to remain inside. |
| `A0 < Amax` and initially admissible state | Finite fuel | The fuel fraction and its `[0,1]` bounds require an ordered, nondegenerate interval. |
| `alpha > 0`, `F > 0`, and usually `mu >= 0` | Connectivity equilibrium | The biological threshold interpretation and positive-equilibrium result otherwise change sign or lose meaning. |

## Scientific premises not supplied by Lean

- A real fire has compact area scaling `A proportional to L^2`.
- Its selected mapped perimeter follows `P proportional to L^(4/3)` on a stated range.
- Mapped perimeter is an adequate proxy for active fireline.
- The latent coherence state corresponds to measured fuel connectivity or active fraction.
- `v_eff = v0 F eta` and `Pa = k C A^(2/3)` describe real fire dynamics.
- Front-associated chemical power is proportional to newly recruited area at stable energy per area.
- Wildfire maximizes the chosen matching index.
- The retained state is sufficient for prediction after weather, fuel, suppression, and observation effects.

These are empirical premises or model closures. Formal implication does not validate them.
