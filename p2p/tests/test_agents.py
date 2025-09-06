from __future__ import annotations

import math
import random

from p2p.agents.prosumer import Prosumer
from p2p.env.devices import Battery, generate_ev_charging_profile_kw
from p2p.env.profiles import (
    household_load_profile_kwh,
    pv_profile_kwh,
    sample_pv_nameplate_kw,
)


def test_load_profile_totals_reasonable() -> None:
    rng = random.Random(42)  # noqa: S311
    prof = household_load_profile_kwh(rng=rng)
    total = sum(prof)
    # 30 kWh/day base with heterogeneity sigma 0.2; expect within [20, 50] kWh
    assert 20.0 <= total <= 50.0


def test_pv_never_exceeds_nameplate_per_interval() -> None:
    rng = random.Random(7)  # noqa: S311
    nameplate = sample_pv_nameplate_kw(rng=rng)
    prof = pv_profile_kwh(nameplate_kw=nameplate, capacity_factor=0.16, rng=rng)
    dt_h = 5 / 60.0
    cap_per_slot = nameplate * dt_h
    assert all(p <= cap_per_slot + 1e-12 for p in prof)
    # Daily energy is in the right ballpark
    total = sum(prof)
    assert 0.12 * nameplate * 24.0 <= total <= 0.20 * nameplate * 24.0


def test_battery_soc_bounds_and_losses() -> None:
    bat = Battery(capacity_kwh=13.5, power_kw=5.0, eta_rt=0.9, soc=0.5, min_soc=0.1)
    # Charge for 1 hour equivalent at power limit 5 kW
    for _ in range(12):  # 12 * 5 min = 1h
        out = bat.step(charge_kw=10.0, discharge_kw=0.0)
    expected_soc = min(1.0, 0.5 + (5.0 * 1.0 * (bat.eta_rt ** 0.5)) / bat.capacity_kwh)
    assert abs(bat.soc - expected_soc) < 1e-6
    # Then discharge hard for 1 hour
    for _ in range(12):
        out = bat.step(charge_kw=0.0, discharge_kw=10.0)
    assert bat.soc >= bat.min_soc - 1e-9
    # Losses are non-negative
    assert out["loss_kwh"] >= 0.0


def test_ev_charging_capped_by_circuit() -> None:
    power = generate_ev_charging_profile_kw(
        arrival_slot=18 * 60 // 5, energy_kwh=12.0, circuit_kw=11.0
    )
    assert max(power) <= 11.0 + 1e-12
    # Delivered energy equals target (within numerical tolerance)
    dt_h = 5 / 60.0
    delivered = sum(p * dt_h for p in power)
    assert math.isclose(delivered, 12.0, rel_tol=1e-6, abs_tol=1e-6)


def test_prosumer_energy_balance_no_battery() -> None:
    # Construct deterministic simple profiles (2 steps)
    load = [1.0, 0.4]
    pv = [0.2, 0.7]
    ev_kw = [0.0, 0.0]
    pr = Prosumer(agent_id="p1", load_kwh=load, pv_kwh=pv, ev_kw=ev_kw)
    # t=0: net = 1.0 - 0.2 = 0.8 (buy)
    n0 = pr.net_at(0)
    assert abs(n0 - 0.8) < 1e-9
    q0 = pr.make_quote(0)
    assert q0 is not None and q0[2] == "buy" and abs(q0[1] - 0.8) < 1e-9
    # t=1: net = 0.4 - 0.7 = -0.3 (sell)
    n1 = pr.net_at(1)
    assert abs(n1 + 0.3) < 1e-9
    q1 = pr.make_quote(1)
    assert q1 is not None and q1[2] == "sell" and abs(q1[1] - 0.3) < 1e-9
