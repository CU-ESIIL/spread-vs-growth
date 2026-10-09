# Latent Constraint Formal Audit

`FireProof.Realization` adds an abstract realization factor without changing the
endogenous growth law.

## Formal results

- `potentialGrowth K A23 = K * A23`.
- `realizedGrowth B K A23 = B * potentialGrowth K A23`.
- If `0 <= B <= 1` and potential factors are nonnegative, realized growth is
  nonnegative and no larger than model-implied potential growth.
- `B=1` recovers the original potential law.
- Dividing observed growth by `A^(2/3)` identifies `B*K`, not the factors.
- `(B,K)=(1/2,2)` and `(1,1)` have identical realized coupling.
- A tighter interval for `B` narrows admissible realized growth.
- Restoration survives a shock only when its contribution is smaller than the
  endogenous restoring contribution.

`B` has no suppression-, water-, fuel-, or management-specific type. The
counterexample formalizes a limitation, not a causal mechanism. Existing pure
scaling results remain valid for potential growth; realized forecasts require
`B=1`, known `B`, or bounds on `B`.
