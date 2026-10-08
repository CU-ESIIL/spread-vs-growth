# Structural Identifiability Audit

## Scope and labels

**Structural identifiability** asks whether ideal, continuous, noise-free
observations uniquely determine states and parameters under the exact model.
**Practical identifiability** asks whether finite noisy data contain enough
information. **Empirical estimability** additionally depends on whether the
remote-sensing products represent the modeled quantities.

This report targets structural identifiability first.

## Area alone

From ideal `A(t)` and `M=A'`, one can calculate

```text
q(t) = M/A^(2/3) = beta0 C F eta.
```

**THEOREM.** The factors are not separately identified by this observation
equation. For any nonzero constant `lambda`,

```text
beta0 -> lambda beta0,
C     -> C/lambda
```

leaves `beta0 C F eta` unchanged. Lean:
`MechanismTests.area_only_product_rescaling`.

More generally, any reciprocal factor transformations whose product is one
leave `A'` unchanged if the factors are treated as latent functions. The full
state equations constrain this freedom, but area alone does not.

**CONDITIONAL THEOREM.** If `Amax` is unknown, even `F(t)` is not observed. Every
candidate `Amax > max A(t)` defines a different fuel path. Using final realized
area as `Amax` makes the state retrospectively available but does not provide a
prospective prediction.

## Adding perimeter

If the observed perimeter is exactly the active perimeter,

```text
P = k C A^(2/3),
```

then `P/A^(2/3)` identifies only `kC`.

**THEOREM.** The transformation

```text
k     -> lambda k,
beta0 -> lambda beta0,
C     -> C/lambda
```

leaves both `P` and `M` unchanged when `F` and `eta` are otherwise latent.
Lean: `MechanismTests.area_perimeter_joint_rescaling`.

If `k` is independently known and mapped `P` truly equals `Pa`, then `C` can be
recovered. Those are strong measurement assumptions, not algebraic results.

The ratio

```text
M/P = (beta0/k) F eta = v0 F eta
```

identifies another product, not `v0`, `F`, and `eta` separately.

## Matching ambiguity

**THEOREM.** `eta(r)=eta(1/r)` for positive `r`. A matching-efficiency value
alone cannot distinguish a connectivity-limited state (`C<F`) from a
fuel-limited state (`C>F`). Lean:
`MechanismTests.matching_reciprocal_symmetry`.

**THEOREM.** The closed forcing is symmetric:

```text
matchedForcing(C,F) = matchedForcing(F,C).
```

Thus an instantaneous normalized growth rate cannot distinguish `C` and `F`
by their contribution to forcing. Their separate dynamics and independent
measurements are essential.

## What becomes identifiable under stronger observations?

| Ideal observation set | Structurally available | Still conditional or ambiguous |
| --- | --- | --- |
| `A` | `A`, `A'`, composite `beta0CFeta` | All four factors; `Amax`; active geometry |
| `A`, `A'` | Same as ideal differentiable `A` | Derivative is not a new structural channel |
| `A`, mapped `P` | Perimeter-area coefficient and local slope | Active fraction, `k`, `C`, and mechanism |
| `A`, true `Pa`, known `k` | `C=Pa/(kA^(2/3))` | Requires active-line measurement and stable `k` |
| Above plus independently defined `Amax` | `F` and model-derived `eta(C/F)` | `beta0` can then be checked for constancy |
| Continuous `C`, `F`, `C'` over varying states | Linear relation `C'/C=alpha(1-C)F-mu` | `alpha` and `mu` separate only if `(1-C)F` varies |

**CONDITIONAL THEOREM.** If `C`, `F`, and `eta` are known and positive over an
interval, then `beta0=M/[CFeta A^(2/3)]` is pointwise identified. Constancy of
that recovered value is itself a falsifiable closure test.

**CONDITIONAL THEOREM.** If `z=(1-C)F` takes at least two distinct values and
`C'/C` is exactly observed, the intercept and slope of
`C'/C=alpha z-mu` identify `alpha` and `mu`. At a single constant `z`, only the
combination `alpha z-mu` is identified.

## Practical and empirical layers

**EMPIRICAL HYPOTHESIS.** `A'`, `A''`, `C'`, and logarithmic
derivatives amplify temporal discretization and perimeter noise. Structural
identifiability under continuous observations does not imply stable estimates
from daily satellite data.

**EMPIRICAL HYPOTHESIS.** Ordinary cumulative fire perimeter includes
inactive, interior, and already extinguished edges. Treating it as `Pa` would
make `C` a model-defined transformation rather than an independently measured
state, weakening any test that then uses `C` to “validate” the model.

## Numerical observational twin

**NUMERICAL RESULT.** In the 750-run dimensionless sweep, the closest retained
pair with materially different connectivity had normalized area RMSE
`9.39e-7` but connectivity RMSE `0.140`. The pair had the same `gamma`, `delta`,
and `x0=0.9`, but `C0=0.5` versus `0.9`. Both rapidly consumed nearly all
available fuel, making their area paths nearly indistinguishable while their
latent connectivity histories remained different.

This is not a theorem of global non-identifiability, but it demonstrates severe
practical non-identifiability even under the exact model.

## Conclusion

From `A(t)` and `P(t)` alone, the general latent quantities `beta0`, `C`, `F`,
and `eta` are not uniquely recoverable. Identification requires independent
`Amax`, active-boundary measurements, a calibrated geometric coefficient, and
the matching/state equations. Those assumptions must be part of the empirical
test rather than silently inferred from the same area trajectory.
