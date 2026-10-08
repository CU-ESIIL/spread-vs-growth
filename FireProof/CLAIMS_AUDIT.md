# Claims Audit

Statuses use the requested vocabulary. “Additional assumptions” means assumptions beyond the algebra printed in the claim, not evidence that the assumptions hold in wildfire.

| SI claim | Lean theorem | Status | Assumptions required | Proof type | Scientific interpretation |
| --- | --- | --- | --- | --- | --- |
| S12 similar-family boundary/content exponent | `Scaling.eliminate_shared_log_size` | PROVED | Positive quantities; shared size; nonzero content exponent | Algebra | Does not transfer a 3D surface exponent to a 2D fire footprint. |
| S13 cumulative footprint union | - | DEFINITION | Event and observation rules | Definition | A footprint records history, not instantaneous combustion. |
| S14 finite-resolution rough-boundary law | - | EMPIRICAL | Scaling range and measurement convention | Empirical closure | Not implied by one perimeter measurement. |
| S15 `sigma=Dh/DA` | `Scaling.eliminate_direct_power_laws` | PROVED | Positive coefficients and shared size; one shared `L`; `DA!=0` | Algebra with real powers | Dimension interpretation needs extra self-similarity evidence. |
| S15 `Dh=4/3`, `DA=2` gives `2/3` | `Scaling.four_thirds_direct_power_law` | PROVED | Same as S15 | Exact arithmetic/algebra | Conditional geometric consequence, not wildfire validation. |
| S16 excess-perimeter slope differs by `1/2` | - | NOT PROVED | Positive differentiable perimeter and area | Calculus identity | Outside the requested smallest kernel. |
| S18-S20 tooth/notch polygon construction | - | NOT PROVED | Nonoverlap and polygon-validity conditions | Constructive geometry | Existing numerical code checks it; no Lean polygon formalization was added. |
| S21 `A'=integral v_n ds` | `Kinematics.boundary_kinematic_identity` | ASSUMED / AXIOMATIZED | Regular moving sets, rectifiable oriented boundary, normal velocity, transport theorem | Named axiom | The full GMT theorem is not disguised as proved. |
| S21 mean-speed and active-fraction reduction | `Kinematics.mean_velocity_reduction`, `active_fraction_reduction` | PROVED | Mean and active fraction definitions; nonempty active set for interpretation | Algebra | Coarse-graining does not independently identify velocity or active fraction. |
| S22 source-augmented kinematics | - | DEFINITION | Source counts only untracked recruitment | Accounting definition | Double-counting resolved spot growth would invalidate it. |
| S23 residual `RA` | - | DEFINITION | Independently measured terms | Definition | A residual is not uniquely a spotting diagnostic. |
| S24 normalized perimeter closure | - | EMPIRICAL | Prespecified objects, range, resolution, and coefficient | Model closure | Must be tested against alternatives. |
| S25 dimensions of `k` | `Units.k_two_thirds` | PROVED | Unit convention | Rational exponent arithmetic | At `2/3`, `k` has length dimension `-1/3`. |
| S26 growth closure from perimeter and kinematics | `ActiveBoundary.active_boundary_substitution` | PROVED | Exact closures; zero untracked source | Ring algebra | Area alone identifies only a product of factors. |
| S27 local slope decomposition | `Identifiability.local_log_slope` | PROVED WITH ADDITIONAL ASSUMPTIONS | Positive differentiable coefficient; differentiable exponent; `x=log a` | Calculus | Changing coefficient or exponent alters observed slope. |
| S27 observed `2/3` implies fixed `sigma=2/3` | `Identifiability.half_plus_one_sixth_counterexample` | FALSE AS STATED | Counterexample has `sigma=1/2`, `kappa proportional to a^(1/6)` | Formal counterexample | Slope alone does not identify geometry or mechanism. |
| S28 constant-beta transformed solution | `Growth.constant_beta_solution_on_interval` | PROVED WITH ADDITIONAL ASSUMPTIONS | Positive differentiable area on a closed interval; fixed exponent; exact ODE | Calculus/mean value theorem | General time-varying beta requires the integral form and was not claimed by this theorem. |
| S29 two-thirds cube-root solution | `Growth.two_thirds_transformed_solution` | PROVED WITH ADDITIONAL ASSUMPTIONS | Same as S28 | Calculus | Cube-root area is affine only while beta is constant and no source acts. |
| S29 cube of transformed solution returns area | `ActiveBoundary.cube_of_positive_rpow_one_third` | PROVED | Positive area | Real-power identity | Fractional-power branch is explicit. |
| S30 exact cubic/quadratic time form | `Growth.shifted_cubic_exact` | PROVED | Nonzero beta; constant `k` for perimeter | Algebra | Exact in shifted time, not exact `A proportional to (t-t0)^3` at early time. |
| S30 late `A proportional to t^3`, `P proportional to t^2` | `Growth.shifted_cubic_ratio_limit`, `shifted_quadratic_ratio_limit` | PROVED | Constant coefficients; time tends to positive infinity | Limit theorem | Rigorous ratio limits replace vague “late time.” |
| S31 finite-speed enclosing-disk bound | - | NOT PROVED | Bounded pointwise speed; local recruitment only; initial enclosing disk | Geometric reachability | Requires a separate moving-front theorem. |
| S32 source-modified cube-root derivative | - | NOT PROVED | Positive differentiable area and continuous source | Calculus | A source adds an explicit `SA/A^(2/3)` term. |
| S39/S44 front-associated chemical-power bridge | - | EMPIRICAL | Independent fuel loading, heat yield, support alignment, residual separation | Physical closure | Constructing power from area growth cannot validate the bridge. |
| S45 power-on-area slope decomposition | `Metabolism.metabolic_relative_derivative` (structural analogue) | PROVED WITH ADDITIONAL ASSUMPTIONS | Positive differentiable factors and nonzero prefactor | Product/power rules | The observed exponent equals geometry only when all other relative derivatives vanish. |
| S49 surface-intersection dimension subtraction | - | ASSUMED / AXIOMATIZED | Generic intersection model and correct geometric objects | Conditional model | Not a projection or wildfire theorem. |
| S50 proposed dimension mappings | - | DEFINITION | Chosen mapping | Definition | A chosen map can place an optimum at any stipulated dimension. |
| S51 matching identity and bound | `Matching.one_sub_eta`, `eta_pos`, `eta_le_one` | PROVED | `r>0` | Field/ring algebra | Algebra does not show fire maximizes the index. |
| S51 unique maximum at `r=1` | `Matching.eta_unique_global_max` | PROVED | `r>0` | Algebra | Unique global maximum of the chosen function only. |
| S52 equal impedances maximize series flux | - | FALSE AS STATED | Fixed driving difference and independently reducible positive impedances | Counterexample in SI | Lowering either resistance increases flux. |
| S53 normalized bridge relation | - | PROVED WITH ADDITIONAL ASSUMPTIONS | Every numerator/denominator factor defined and bridge closure accepted | Dimensional algebra | Interpretable normalization does not derive the bridge. |
| S54 area-weighted connectivity | - | DEFINITION | Positive patch areas and specified graph rule | Definition | Does not measure heat transfer by itself. |
| S55 fast-adjustment separation | - | EMPIRICAL | Measurable time scales and positive growth | Empirical hypothesis | Larger size does not prove short memory. |
| S56 remaining-fuel endpoints | `Fuel.remaining_at_initial`, `remaining_at_max` | PROVED | `Amax!=A0` for the initial ratio | Field algebra | Bookkeeping only. |
| S56 `0<=F<=1` | `Fuel.remaining_mem_unit` | PROVED | `A0<Amax`, `A in [A0,Amax]` | Order algebra | The area interval is a premise here. |
| S56 connectivity vector field boundary signs | `Connectivity.boundary_signs` | PROVED | `mu>=0` | Algebra | Necessary check, not a complete invariance proof. |
| S56 `[0,1]` is dynamically invariant | `Connectivity.unit_interval_invariant_with_barrier_assumptions` | PROVED WITH ADDITIONAL ASSUMPTIONS | Initial state in interval; crossing continuity; forward uniqueness/barriers | Order/analysis | Boundary signs alone do not establish it. |
| S56 positive equilibrium formula | `Connectivity.positiveEquilibrium_is_equilibrium` | PROVED | `alpha F != 0` | Field/ring algebra | Candidate equilibrium may be inadmissible. |
| S56 threshold `F>mu/alpha` | `Connectivity.positiveEquilibrium_pos_iff`, `threshold_form` | PROVED | `alpha>0`, `F>0` | Ordered-field algebra | Positive equilibrium disappears at or below threshold. |
| S57 active-boundary construction | `ActiveBoundary.active_boundary_substitution` | PROVED | All displayed closure equalities | Ring algebra | Does not validate the closures. |
| S58 cube-root cancellation | `ActiveBoundary.cube_root_removes_explicit_area` | PROVED WITH ADDITIONAL ASSUMPTIONS | Positive differentiable area; exact two-thirds law | Chain rule | Cancellation is exact inside the construction. |
| S58 fuel derivative | `Fuel.remaining_derivative` | PROVED | Constant nondegenerate fuel interval for interpretation | Derivative rule | Does not itself keep area below `Amax`. |
| S58 area cannot cross `Amax` because rate vanishes there | `Fuel.cannot_cross_with_explicit_barrier_assumptions` | PROVED WITH ADDITIONAL ASSUMPTIONS | Intermediate-value crossing and forward uniqueness/barrier | Analysis | The manuscript's stated reason is incomplete. |
| S59 metabolic log derivative | `Metabolism.metabolic_relative_derivative` | PROVED WITH ADDITIONAL ASSUMPTIONS | Strict positivity, differentiability, nonzero `beta0` | Product and real-power rules | Peak/decline interpretation remains scientific, not logical necessity. |
| Active perimeter log derivative | `Metabolism.active_perimeter_relative_derivative` | PROVED WITH ADDITIONAL ASSUMPTIONS | Strict positivity, differentiability, nonzero `k` | Product and real-power rules | Exact mathematical decomposition. |
| S74 kinematic/metabolic residuals | - | DEFINITION | Independently estimated terms | Definition | Circularly defined velocity or power cannot test the residual. |
| S75 residual conditional moments near zero | - | EMPIRICAL | Sampling model and independent data | Statistical hypothesis | Not a theorem. |
| S76 held-out added-value scores | - | DEFINITION | Prespecified loss and leakage-safe split | Definition | Positive gain is an empirical result. |
| S87 completed chain | Multiple modules | PROVED WITH ADDITIONAL ASSUMPTIONS | Mix of definitions, named axiom, closures, and empirical premises | Layered | The chain's links do not share one evidential status. |
| “Wildfire is metabolic” | - | EMPIRICAL | Independent geometry, consumption, power, and prediction evidence | Scientific hypothesis | Lean proves only internal consequences of supplied premises. |

## Second-stage adversarial claims

| SI or narrative claim | Lean theorem / analysis | Status | Assumptions required | Proof type | Scientific interpretation |
| --- | --- | --- | --- | --- | --- |
| `M'=0` exactly when the logarithmic balance is zero | `Lifecycle.peak_iff_balance_zero` | THEOREM | `M!=0`; valid relative-derivative identity | Algebra | Characterizes a peak candidate; does not guarantee existence or maximality. |
| Matching gives the reduced peak balance | `Lifecycle.closed_peak_balance` | CONDITIONAL THEOREM | Positive states; differentiability; exact fuel, connectivity, and matching closures | Algebra after calculus identity | Produces a prospective sign test only if latent states are independently available. |
| The model guarantees initial acceleration | Numerical sweep and `Lifecycle.acceleration_sign_is_balance_sign` | COUNTEREXAMPLE | None beyond admissible parameter choices | Sign analysis and numerical counterexample | 312/750 swept trajectories declined monotonically. |
| The model guarantees an interior metabolic maximum | Numerical sweep | COUNTEREXAMPLE | Admissible positive initial states | Numerical counterexample | The maximum can occur at ignition or beyond a finite observation horizon. |
| The model guarantees a unique maximum | Numerical sweep | NUMERICAL RESULT | Closed two-state model on tested grid | Parameter sweep | No multiple peaks found, but uniqueness is not proved. |
| Extinction occurs in finite time | Differential-inequality analysis | COUNTEREXAMPLE | Smooth closed ODE; positive initial `C,F`; bounded state | Conditional analysis | The unchanged model approaches zero asymptotically; abrupt death requires another process or threshold. |
| Matching closure reduces forcing to a harmonic form | `MechanismTests.matchedForcing_closed_form` | THEOREM | Positive `C,F` | Algebra | `M/A^(2/3)=beta0[2CF/(C+F)]^2` is a stronger test than exponent fitting. |
| Growth identifies which side of matching is limiting | `MechanismTests.matchedForcing_symmetric`, `matching_reciprocal_symmetry` | COUNTEREXAMPLE | Positive states | Formal symmetry | Instantaneous growth cannot distinguish `C<F` from `C>F`. |
| `beta0,C,F,eta` are separately identified from area | `MechanismTests.area_only_product_rescaling` | COUNTEREXAMPLE | Nonzero rescaling | Formal invariance | Area identifies only `beta0CFeta`. |
| Area plus active perimeter identifies all factors | `MechanismTests.area_perimeter_joint_rescaling` | COUNTEREXAMPLE | Unknown `k`; latent `F,eta` | Formal invariance | It identifies `kC` and `(beta0/k)Feta`, not each factor. |
| `delta>=1` is extinction dominated | `Dimensionless.no_connectivity_recruitment_of_one_le_delta` | THEOREM | Biological unit square | Ordered algebra | Connectivity cannot increase anywhere, although area may still grow temporarily. |
| Positive connectivity equilibrium exists for `F>delta` | `Dimensionless.fuel_threshold_for_positive_equilibrium` | THEOREM | `F>0` | Ordered-field algebra | Exact dimensionless threshold for the frozen-fuel subsystem. |
| `P~A^(2/3)`, `A~t^3`, and `P~t^2` are independent evidence | `MechanismTests.cubic_quadratic_headlines_are_dependent` | COUNTEREXAMPLE | Exact cubic/quadratic parameterization | Algebra | The third exponent follows from the other two. |
| All three powers uniquely identify fire metabolism | `MechanismTests.kinematic_alternative_all_three` | COUNTEREXAMPLE | Purely kinematic construction | Formal construction | An accelerating characteristic length and rough boundary reproduce all three. |
| Peak-balance closure predicts held-out fire transitions | - | EMPIRICAL HYPOTHESIS | Independent active boundary, `Amax`, parameters, and held-out data | Prospective empirical test | This is the strongest proposed discrimination test, not yet validated. |
| Closed forcing is symmetric in coherence and fuel | `MechanismTests.matchedForcing_symmetric` | THEOREM | Positive `C,F` | Algebra | Instantaneous normalized growth cannot identify which side is limiting. |
| Matching equality maximizes total forcing | `MechanismTests.closedForcing_hasDerivAt_C` | COUNTEREXAMPLE | Positive `C,F` | Formal derivative | `eta` peaks at equality, but `G=CFeta` increases in either state and saturates. |
| Closed forcing at equality is `s^2` | `MechanismTests.closedForcing_at_match` | THEOREM | `s!=0` | Algebra | Equality is a reference state, not a total-forcing optimum. |
| Closed forcing is bounded by `CF` | `MechanismTests.matchedForcing_le_product` | THEOREM | Positive `C,F` | Ordered algebra | This is the direct consequence of `eta<=1`. |
| Peak condition contains no independent `eta'` term after closure | `Dimensionless.peakBalance_eq_transitionBalance` | THEOREM | Positive/nonzero states and exact matching, fuel, and coherence equations | Algebraic reduction | `Psi_d=0` is the compact dimensionless transition surface. |

## Axiom boundary

The custom scientific axiom set contains exactly `FireProof.Kinematics.boundary_kinematic_identity`. Standard Lean/Mathlib logical axioms may appear in `#print axioms` output; they are not additional wildfire assumptions. No theorem marked `PROVED` depends on the custom kinematics axiom unless it is explicitly a kinematics reduction.
