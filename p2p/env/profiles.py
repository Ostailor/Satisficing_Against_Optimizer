from __future__ import annotations

import math
import random


def diurnal_load_shape(steps: int, step_min: int) -> list[float]:
    """Unitless diurnal shape with morning/evening peaks."""
    shape = []
    for i in range(steps):
        t = i * step_min / 60.0
        morning = math.exp(-((t - 8.0) ** 2) / 6.0)
        evening = math.exp(-((t - 19.0) ** 2) / 6.0)
        shape.append(0.3 + 0.5 * morning + 0.7 * evening)
    return shape


def household_load_profile_kwh(
    *,
    minutes: int = 24 * 60,
    step_min: int = 5,
    base_kwh_per_day: float = 30.0,
    rng: random.Random | None = None,
) -> list[float]:
    """Generate a household load profile summing to ~base_kwh_per_day with heterogeneity.

    Heterogeneity via log-normal scaler with sigma ~ 0.2 (moderate dispersion).
    """
    rng = rng or random.Random(0)  # noqa: S311
    steps = minutes // step_min
    shape = diurnal_load_shape(steps, step_min)
    s = sum(shape)
    # Log-normal scaler
    sigma = 0.2
    scale = math.exp(rng.gauss(0.0, sigma))
    target = base_kwh_per_day * scale
    return [v * (target / s) for v in shape]


def clear_sky_bell(steps: int, step_min: int) -> list[float]:
    out = []
    for i in range(steps):
        t = i * step_min / 60.0
        out.append(max(0.0, math.exp(-((t - 12.0) ** 2) / 8.0)))
    return out


def lognormal_params_from_quantiles(median: float, p20: float, p80: float) -> tuple[float, float]:
    """Return (mu, sigma) for lognormal given median and 20th/80th percentiles.

    median = exp(mu). For p20, p80: exp(mu + sigma*z_q).
    z_0.8 ≈ 0.84162; z_0.2 ≈ -0.84162; difference ≈ 1.68324.
    """
    z80 = 0.8416212335729143
    z20 = -0.8416212335729143
    sigma = (math.log(p80) - math.log(p20)) / (z80 - z20)
    mu = math.log(median)
    return mu, sigma


def sample_pv_nameplate_kw(
    *, rng: random.Random, median: float = 7.4, p20: float = 5.0, p80: float = 11.0
) -> float:
    mu, sigma = lognormal_params_from_quantiles(median, p20, p80)
    # Draw from lognormal with these params
    return math.exp(rng.gauss(mu, sigma))


def pv_profile_kwh(
    *,
    nameplate_kw: float,
    capacity_factor: float = 0.16,
    minutes: int = 24 * 60,
    step_min: int = 5,
    noise_std: float = 0.05,
    rng: random.Random | None = None,
) -> list[float]:
    """Generate a PV energy profile (kWh per interval).

    - Total daily energy ≈ nameplate_kw * 24h * capacity_factor.
    - Shape given by clear-sky bell; multiplicative noise; clipped at nameplate*dt.
    """
    rng = rng or random.Random(0)  # noqa: S311
    steps = minutes // step_min
    dt_h = step_min / 60.0
    bell = clear_sky_bell(steps, step_min)
    s = sum(bell)
    if s <= 0:
        return [0.0] * steps
    target_kwh = nameplate_kw * 24.0 * capacity_factor
    base = [b * (target_kwh / s) for b in bell]
    # Apply noise and clip at nameplate limit per interval
    out = []
    max_kwh = nameplate_kw * dt_h
    for v in base:
        eps = rng.gauss(0.0, noise_std)
        val = max(0.0, v * (1.0 + eps))
        out.append(min(val, max_kwh))
    return out
