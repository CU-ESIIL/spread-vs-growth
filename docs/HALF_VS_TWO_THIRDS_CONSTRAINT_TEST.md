# Why Does One-Half Sometimes Beat Two-Thirds?

## Executive verdict

**Outcome C: one-half remains competitive during near-potential growth, so
unresolved realization deficits do not explain its performance.**

The held-out test contains 4,041 slope transitions from 731 fires matched to an
origin-safe future-growth residual. Define `D=L(1/2)-L(2/3)`; negative `D` means
one-half predicted better. Across transitions, `q` and `D` had Spearman
`rho=-0.128`. In the upper quartile of `q`, mean `D=-0.0376` and one-half won
61.3%. In the strongest lower decile, mean `D=+0.0055` and one-half won 33.3%.

That direction is opposite the simple constraint-mixture prediction. Results
vary by lead and long-lead cells are noisy, but the central falsification test
fails: two-thirds does not clearly regain an advantage near model-implied
potential.

## Design and diagnostics

Potential growth came from the best past-only empirical model, not from forcing
geometry toward 2/3. `D=f(q)` is retrospective mechanism discrimination;
origin-time age, area, geometry, and OT tests are kept separate.

Progressive filtering used development/calibration residual quantiles. Removing
the strongest deficits did not produce a monotonic shift toward 2/3. Flexible
dynamics remained the necessary comparator and was often better than either
fixed center.

- Deficits become somewhat more common with age in the matched slope sample;
  area contributes little after age and lead are included.
- Mapped boundary productivity declines during strong deficits.
- Exterior-versus-total perimeter sensitivity persists across residual strata.
- Contemporaneous OT is associated with `q` (`rho=0.496`) and `D`
  (`rho=-0.295`) on 378 transitions, but this is not early warning.
- Prior OT had almost no held-out association with future `q` (`rho=0.0355`).

| Question | Verdict |
|---|---|
| Is one-half established as a physical attractor? | NOT SUPPORTED |
| Is its advantage concentrated in negative residuals? | NOT SUPPORTED |
| Does two-thirds become better near potential growth? | NOT SUPPORTED |
| Is slope drift confined to deficit intervals? | NOT SUPPORTED |
| Do deficits increase with age or size? | PARTIALLY SUPPORTED for age |
| Does mapped-boundary productivity decline? | SUPPORTED descriptively |
| Is perimeter sensitivity confined to deficits? | NOT SUPPORTED |
| Does OT provide early warning? | NOT SUPPORTED |
| Does the mixture improve long horizons? | NOT SUPPORTED |
| Can FIRED identify the cause? | NOT IDENTIFIABLE |

The remaining explanations are a genuine lower-exponent regime, lifecycle
change, and observation/estimator effects. This test cannot choose one, but it
rejects unresolved growth deficits as a sufficient explanation.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPATH=src ../cubedynamics/.venv/bin/python \
  scripts/run_half_vs_two_thirds_constraint_test.py
```

Outputs are in `outputs/half_vs_two_thirds_constraint_test/`.

