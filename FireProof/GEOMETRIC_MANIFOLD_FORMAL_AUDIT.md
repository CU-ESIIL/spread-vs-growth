# Geometric manifold formal audit

## Verdict

The Lean project does **not** prove that observed wildfire slopes converge to two-thirds. It proves conditional algebra after the exponent or closure has been assumed. The generic attractor module proves restoration only when a restoring update equation is supplied as a hypothesis, and explicitly does not select a numerical equilibrium.

## What is formalized

`THEORY_CORE.md` derives the geometric closure

\[
P=kA^{2/3}
\]

from shared-size assumptions `A=c_A L^2`, `P=c_P L^(4/3)`, and constant coefficients, with `k=c_P/c_A^(2/3)`. This is a conditional elimination identity.

`FireProof/Growth.lean` proves transformed growth solutions for an assumed law `A'=beta A^sigma`, including the specialization `sigma=2/3`. It does not infer `sigma` from data.

`FireProof/Attractor.lean` defines a generic target `sigmaStar`. `linear_step_restores` and the Lyapunov theorem require the update

\[
\sigma_{t+1}-\sigma_t=-\lambda(\sigma_t-\sigma_*)
\]

as a premise. `attraction_math_does_not_select_two_thirds` makes the dependency explicit: the algebra is generic in `sigmaStar`.

## What is not established

No theorem derives any of the following from `P=kA^(2/3)` alone:

- a noisy rolling estimator converges to 2/3;
- fire-specific slopes share one distributional mean;
- cumulative mapped perimeter equals active fireline;
- the coefficient is constant across fires, time, resolution, or perimeter convention;
- two-thirds identifies metabolism, optimization, coherence, or restoration.

Therefore:

\[
P\propto A^{2/3}\not\Rightarrow\hat\sigma_t\rightarrow2/3.
\]

The first statement is a relationship between `P` and `A`; the second requires an additional dynamical law for either the true local derivative or its estimator.

## Constant versus varying coefficient

The closure used in the current geometric derivation has constant coefficients over the claimed scaling range. If instead

\[
P=k(A)A^{2/3},
\]

then, wherever derivatives exist,

\[
\frac{d\log P}{d\log A}=\frac23+\frac{d\log k}{d\log A}.
\]

The empirical `Z_2/3=log k(A)` drift is therefore diagnostic of coefficient change, not restoration. A local slope below two-thirds means `k(A)` is decreasing over that interval. This identity carries no mechanistic interpretation by itself.

The present Lean project does not need modification to accommodate the empirical result. The dependency is already conditional: constant `k`, fixed exponent, and generic restoring dynamics are separate assumptions. Any future theorem connecting the closure to an attractor must state a law for `k(A,t)` or `sigma_t` explicitly and cannot import two-thirds by notation.

## Dependency classification

| Statement | Formal status | Empirical implication |
| --- | --- | --- |
| Shared-size elimination gives `P=kA^(2/3)` | Proved under stated geometric assumptions | Test the specified perimeter over a prespecified range |
| `A'=beta A^sigma` gives transformed linearity | Proved conditional on growth law | Does not estimate or identify `sigma` |
| Linear restoring update decreases deviation | Proved conditional on update and `0<lambda<2` | Does not show wildfires follow the update |
| Target equals 2/3 | Not selected by attractor algebra | Must be estimated or independently derived |
| Mapped `Z_2/3` is coherence or metabolism | Not formalized or identifiable | Requires independent active-line/state measurements |

## Audit conclusion

The new empirical result weakens the mapped-perimeter closure at Level 1 of `PREDICTION_HIERARCHY.md`; it does not invalidate the kinematic identity or the broader energy-accounting algebra. The theory must specify its boundary object and coefficient stability before treating two-thirds as a within-fire prediction.
