# Final Scientific Synthesis

## 1. What is the minimal theory?

The generative theory is a two-state ODE for cumulative area `A` and latent
coherence `C`:

```text
F = (Amax-A)/(Amax-A0),
G(C,F) = [2CF/(C+F)]^2,
A' = beta0 G(C,F) A^(2/3),
C' = alpha C(1-C)F-mu C.
```

Everything else is either a proposed derivation of the `2/3` factor, an
algebraic output, an observation equation, or an energetic interpretation.

## 2. What is the central mathematical result?

The matching factor closes exactly:

```text
CFeta(C/F) = [2CF/(C+F)]^2.
```

This turns four apparently separate growth factors into a symmetric forcing
surface. It reveals quadratic limitation by the smaller state, monotonicity in
each state, saturation, and an instantaneous ambiguity between coherence and
fuel limitation.

## 3. What is the strongest unique prediction?

The strongest comparatively distinctive prediction is joint agreement with

```text
A'/A^(2/3) = beta0 G(C,F),
C'/C = alpha(1-C)F-mu,
sign(M') = sign(Psi).
```

The final sign equation is dependent on the first two, but its prospective
success would show that their combination constrains a future transition.

## 4. What is the weakest headline prediction?

`P~A^(2/3)` is the weakest. It can arise from several geometries, changing
coefficients, elongation, fragmentation, or explicit non-metabolic
constructions. The related `t^3` and `t^2` laws are constant-forcing special
cases and are algebraically redundant with the perimeter-area relation.

## 5. What does “fire life cycle” mean mathematically?

It should mean movement through a state-dependent acceleration balance, not a
universal trajectory shape:

```text
Psi>0: metabolic rate accelerates,
Psi=0: stationary metabolic rate,
Psi<0: metabolic rate decelerates.
```

A local maximum requires a crossing from positive to negative. The model does
not guarantee initial acceleration, an interior peak, or peak uniqueness.

## 6. What observation most directly falsifies the mechanism?

After independently measuring active coherence and prospectively defining
remaining connected fuel, fit parameters on development fires. Repeated wrong
held-out predictions of the sign of `M'`, together with structured residuals
from the normalized forcing and coherence equations, would directly falsify
the closed mechanism. A slope different from `2/3` tests only its geometric
entry point.

## 7. What is the smallest measurement set?

The minimum discriminating set is:

1. repeated cumulative burned area at sufficient temporal resolution;
2. independently mapped active perimeter, not only cumulative perimeter;
3. a prospectively delineated reachable connected-fuel domain defining `Amax`;
4. an independently calibrated coherence measure or a validated mapping from
   active perimeter to `C`;
5. development data for `k`, `beta0`, `alpha`, and `mu` plus held-out fires.

Weather, suppression, and detection information are needed to interpret
failure and abrupt endings, even if they are not states in the minimal model.

## 8. Which claim should be strengthened?

Strengthen the manuscript’s falsifiable state-closure claim. State and test the
closed forcing surface and the prospective transition equation explicitly.
These are sharper than saying only that fuel and connectivity modulate growth.

Also state the new consequence that the smooth positive-state model predicts
asymptotic rather than finite-time extinction. This gives abrupt termination a
clear diagnostic meaning.

## 9. Which claim should be weakened?

Weaken every suggestion that the model intrinsically generates a universal
recruitment-acceleration-peak-decline sequence. That sequence occurs only in
part of state and parameter space. Also weaken any presentation of the three
headline exponent laws as separate evidence.

## 10. What can be removed without predictive loss?

`F`, `r`, `eta`, and `M` need not be independent states: they are determined by
`A`, `C`, and definitions. `Pa` and `v_eff` are valuable observation equations
but are not needed to integrate the canonical ODE. `L`, `cA`, and `cP` can be
removed after deriving `k` and the exponent. The dynamic state `C` cannot be
removed without reducing the model to an unconstrained time-varying
coefficient and losing its principal mechanistic predictions.

## Single best conceptual figure

Use a `C-F` phase-plane figure with both axes running from zero to one.

- **Background:** color contours of `G(C,F)=[2CF/(C+F)]^2`, zero on either
  axis and increasing toward the upper-right corner.
- **Diagonal:** the line `C=F`, labeled “maximum matching efficiency, not
  maximum total forcing.”
- **Connectivity nullcline:** `F=delta/(1-C)` where it lies inside the square.
  Horizontal arrows point toward increasing or decreasing `C` on the correct
  sides.
- **Fuel direction:** vertical arrows point downward because `F` decreases
  while area grows.
- **Acceleration transition:** overlay three `Psi_d=0` contours for early,
  intermediate, and late normalized area `x`. Label the `Psi_d>0` and
  `Psi_d<0` sides rather than drawing one guaranteed lifecycle path.
- **Trajectories:** show at least three: rise-peak-decline, monotone decline,
  and slow continued growth. Mark stationary-rate crossings where they occur.
- **Geometry annotation:** a side arrow from `P~A^(2/3)` to the normalization
  `M/A^(2/3)` makes clear that geometry is divided out before the state forcing
  is tested.
- **Failure annotations:** identify the zero-forcing axes, the region with no
  connectivity recruitment, and a trajectory that never crosses the
  acceleration surface during the displayed interval.

This one figure would explain geometry, forcing, state dynamics, and lifecycle
transitions while visibly refusing to imply that every fire follows one path.

## Bottom line

The theory is mathematically coherent as a conditional two-state closure. Its
headline exponent is not mechanism-specific, its lifecycle is not universal,
and its latent states are not recoverable from area and mapped perimeter alone.
Its scientific value rests on a harder but genuinely discriminating test:
independent state measurements must satisfy the forcing surface and coherence
dynamics strongly enough to predict held-out acceleration transitions.
