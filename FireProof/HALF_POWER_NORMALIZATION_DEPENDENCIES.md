# Half-Power Normalization Dependency Map

## Two-thirds geometric chain

```text
positive A, P, L, cA, cP
one shared characteristic size L
A = cA L^2
P = cP L^(4/3)
            |
            v
Scaling.four_thirds_direct_power_law
P = [cP / cA^(2/3)] A^(2/3)
            |
            +-- pointwise identity: no constancy across observations required
            |
            +-- scaling law over a domain additionally requires
                k = cP/cA^(2/3) to remain fixed on that domain
                        |
                        +-- within-fire prediction: fixed k_i during growth
                        +-- between-fire prediction: restrictions on k_i across fires
                        +-- population law: common k or an explicit coefficient model
```

The existing theorem proves the algebra above the fork. It does not prove any
of the three empirical coefficient restrictions below it.

## One-half Euclidean chain

```text
positive A, P, L, cA, cP
one shared characteristic size L
A = cA L^2
P = cP L
            |
            v
Normalization.euclidean_one_half_elimination
P = [cP / cA^(1/2)] A^(1/2)
            |
            +-- fixed coefficient: geometric-similarity law on a domain
            +-- fire-specific fixed coefficient: parallel fire trajectories
            +-- variable coefficient: exponent is not identifying
            +-- no implication to diffusion without an independent process model
```

## Origin anchoring chain

```text
positive observed origin (A0,P0)
candidate exponent sigma
            |
            v
c_sigma,0 = P0/A0^sigma
P_sigma(A) = P0(A/A0)^sigma
            |
            +-- P_sigma(A0)=P0 for every sigma
            +-- c_sigma,0 depends on sigma
            +-- agreement at A0 cannot identify sigma
            |
            v
P_sigma2(A)/P_sigma1(A)=(A/A0)^(sigma2-sigma1)
            |
            v
P_2/3(A)/P_1/2(A)=(A/A0)^(1/6)
```

The empirical prediction is not “anchoring supports the chosen exponent.” It
is that discrimination should increase with prospectively observed area
expansion. A near-tie at low expansion is weak evidence because the candidate
curves are mathematically close by construction.

## Variable-normalization non-identification

```text
positive area A
arbitrary observed perimeter P
arbitrary exponent sigma
            |
            v
k_sigma = P/A^sigma
            |
            v
P = k_sigma A^sigma
```

This exact reconstruction is mathematical non-identification. Statistical
identification requires restrictions on `k`, repeated observations with
leverage, a prespecified coefficient model, and measurement assumptions; Lean
does not adjudicate those data questions.

## Active-boundary chain

```text
Pa = k C(t) A^(2/3)
veff = v0 F eta
beta0 = v0 k
areaRate = veff Pa
            |
            v
ActiveBoundary.active_boundary_substitution
areaRate = beta0 C F eta A^(2/3)
```

Here `k` is scalar but `C(t)` is a dynamic state. Therefore the active
perimeter's effective normalization is `kC(t)`. The dependency

```text
Metabolism.active_perimeter_relative_derivative
Pa'/Pa = C'/C + (2/3) A'/A
```

shows why the closure does not predict a local active-perimeter slope exactly
equal to `2/3` unless `C` is locally constant. No theorem equates cumulative
mapped perimeter with `Pa`.

## Manuscript-relevant claim map

| Claim | Assumptions | Formal theorem/status | Empirical prediction |
|---|---|---|---|
| `P=kA^(2/3)` | shared `L`; positive constants; `DA=2,Dh=4/3` | `Scaling.four_thirds_direct_power_law` | measure slope and coefficient stability under a prespecified perimeter rule |
| Fixed two-thirds law during one fire | preceding assumptions plus constant `k_i` through growth | conditional consequence, not a separate theorem object | zero drift of `log P-(2/3)log A` within fires |
| Common population two-thirds law | preceding assumptions plus one common `k` | not formalized | development-lock `k`; score held-out fires without refitting |
| Fire-specific two-thirds law | one constant `k_i` per fire | coherent but not typed | parallel within-fire trajectories with heterogeneous intercepts |
| `P=kA^(1/2)` | shared `L`; `DA=2,Dh=1`; stable coefficient | `Normalization.euclidean_one_half_elimination` | same common/fire-specific tests as two-thirds |
| One-half means diffusion | independent diffusion theorem and observation mapping | absent | process-specific validation; exponent alone is insufficient |
| Anchored one-half extrapolation | positive `(A0,P0)` | `Normalization.anchoredPrediction_at_origin` | local conditional forecast, not common-law evidence |
| Anchored half/two-thirds separation | positive origin and target area | `Normalization.half_two_thirds_anchored_ratio` | separation grows as `(A/A0)^(1/6)` |
| Any exponent with arbitrary `k(A)` | positive area | `Normalization.variable_normalization_reconstructs` | no exponent identification without restrictions on `k` |
| Local two-thirds slope | active closure plus locally constant `C` and correct perimeter object | not implied generally; derivative theorem adds `C'/C` | test state derivative and perimeter mapping |
| Return to two-thirds | independent restoring dynamics with center `2/3` | not selected by `Attractor`; generic in center | held-out local-slope transition forecast |

## Required empirical separation

Every future claim should state all four fields:

1. exponent;
2. normalization source;
3. index over which normalization may vary;
4. domain over which it is held fixed.

Recommended labels are:

- **population one-half law** for a coefficient locked before test fires;
- **fire-conditioned one-half scaling** for one constant fitted coefficient per
  fire;
- **origin-anchored one-half extrapolation** for a coefficient determined by
  the current point;
- **one-half local-slope shrinkage** for a future derivative target;
- **one-half temporal area-growth model** for `A'=beta A^(1/2)`.

