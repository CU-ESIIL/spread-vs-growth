"""Full-precision reproduction of the seven hypothetical SI examples."""

from __future__ import annotations

import math

from .forecasting import calibrate_beta_two_thirds, forecast_two_thirds
from .growth import beta_for_target, constant_beta_area, rate_change_ratio


DAY_SECONDS = 86400.0
HECTARE_M2 = 10000.0
KILOMETRE_M = 1000.0


def reproduce_worked_examples() -> dict[str, object]:
    area0 = 100.0
    area3 = 2700.0
    perimeter0 = 4.0
    perimeter3 = 36.0
    power = 5e9
    air_temperature = 305.0
    sigma = math.log(perimeter3 / perimeter0) / math.log(area3 / area0)
    beta = calibrate_beta_two_thirds(area0, area3, 0.0, 3.0)
    k = perimeter0 / area0 ** (2 / 3)

    def state(day: float) -> dict[str, float]:
        area = float(constant_beta_area(day, area0, beta, 2 / 3))
        area_rate = beta * area ** (2 / 3)
        perimeter = k * area ** (2 / 3)
        return {
            "day": day,
            "area_ha": area,
            "perimeter_km": perimeter,
            "area_rate_ha_day": area_rate,
            "perimeter_area_km_ha": perimeter / area,
        }

    trajectory = [state(day) for day in (0.0, 3.0, 4.0, 5.0)]
    day0, day3, day4, day5 = trajectory
    acceleration3 = (2 / 3) * beta**2 * area3 ** (1 / 3)
    effective_speed_m_day = day3["area_rate_ha_day"] * HECTARE_M2 / (perimeter3 * KILOMETRE_M)
    energy_area0 = power * DAY_SECONDS / (day0["area_rate_ha_day"] * HECTARE_M2)
    energy_area3 = power * DAY_SECONDS / (day3["area_rate_ha_day"] * HECTARE_M2)
    stopping_area = 5000.0
    remaining_time = 3 * (stopping_area ** (1 / 3) - area3 ** (1 / 3)) / beta
    frozen_time = (stopping_area - area3) / day3["area_rate_ha_day"]
    reduced_area5 = forecast_two_thirds(area0, 0.8 * beta, 5.0)
    ratio = rate_change_ratio(area0, beta, 0.8, 5.0)
    beta_day0_target = beta_for_target(area0, stopping_area, 5.0)
    beta_day3_target = beta_for_target(area3, stopping_area, 2.0)

    return {
        "inputs": {"area0_ha": area0, "area3_ha": area3, "perimeter0_km": perimeter0, "perimeter3_km": perimeter3, "power_w": power, "air_temperature_k": air_temperature},
        "example_1": {"sigma_hat": sigma},
        "example_2": {
            "beta_hat_ha_one_third_day": beta,
            "k_hat_km_ha_minus_two_thirds": k,
            "area_rate_day3_ha_day": day3["area_rate_ha_day"],
            "effective_speed_m_day": effective_speed_m_day,
            "effective_speed_m_s": effective_speed_m_day / DAY_SECONDS,
            "acceleration_day3_ha_day2": acceleration3,
        },
        "example_3": {"area_day4_ha": day4["area_ha"], "area_day5_ha": day5["area_ha"]},
        "example_4": trajectory,
        "example_5": {
            "power_over_temperature_w_k": power / air_temperature,
            "power_over_perimeter_w_m": power / (perimeter3 * KILOMETRE_M),
            "energy_per_area_day0_j_m2": energy_area0,
            "energy_per_area_day3_j_m2": energy_area3,
        },
        "example_6": {"remaining_time_days": remaining_time, "frozen_rate_time_days": frozen_time},
        "example_7": {
            "reduced_area_day5_ha": reduced_area5,
            "reduced_to_baseline_ratio": ratio,
            "naive_late_time_ratio": 0.8**3,
            "beta_max_from_day0": beta_day0_target,
            "rho_max_from_day0": beta_day0_target / beta,
            "reduction_from_day0": 1 - beta_day0_target / beta,
            "beta_max_from_day3": beta_day3_target,
            "rho_max_from_day3": beta_day3_target / beta,
            "reduction_from_day3": 1 - beta_day3_target / beta,
        },
    }
