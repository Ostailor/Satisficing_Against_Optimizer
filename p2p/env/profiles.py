from __future__ import annotations


def diurnal_load_profile(minutes: int = 24 * 60, step_min: int = 5) -> list[float]:
    """Toy diurnal load shape: peaks at 8:00 and 19:00 (relative units).

    Returns kWh per interval for a 30 kWh/day household scaled roughly.
    """
    steps = minutes // step_min
    import math

    base = []
    for i in range(steps):
        t = i * step_min / 60.0
        morning = math.exp(-((t - 8.0) ** 2) / 6.0)
        evening = math.exp(-((t - 19.0) ** 2) / 6.0)
        val = 0.3 + 0.5 * morning + 0.7 * evening
        base.append(val)
    s = sum(base)
    scale = 30.0 / s  # target 30 kWh/day
    return [v * scale for v in base]


def clear_sky_pv_profile(minutes: int = 24 * 60, step_min: int = 5) -> list[float]:
    """Toy clear-sky PV production (kWh per interval) for 7.4 kW nameplate.

    Single bell curve centered at noon; purely illustrative for smoke.
    """
    steps = minutes // step_min
    import math

    out = []
    for i in range(steps):
        t = i * step_min / 60.0
        bell = math.exp(-((t - 12.0) ** 2) / 8.0)
        out.append(max(0.0, bell) * (7.4 * (step_min / 60.0)) * 0.5)
    return out
