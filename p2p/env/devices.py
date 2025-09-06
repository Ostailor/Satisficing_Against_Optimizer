from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Battery:
    capacity_kwh: float
    power_kw: float
    eta_rt: float = 0.9
    soc: float = 0.5  # 0..1
    min_soc: float = 0.1

    def __post_init__(self) -> None:
        self.eta_chg = self.eta_rt ** 0.5
        self.eta_dis = self.eta_rt ** 0.5

    def bounds(self) -> tuple[float, float]:
        return (self.min_soc, 1.0)

    def step(
        self,
        *,
        charge_kw: float = 0.0,
        discharge_kw: float = 0.0,
        dt_h: float = 5.0 / 60.0,
    ) -> dict:
        """Advance battery state one interval.

        - Enforces power limits and SoC bounds.
        - Returns dict with actual charge/discharge kW, energy flows, and losses.
        - Energy balance (stored) is respected: ΔE_stored = E_in_stored − E_out_stored.
        """
        if charge_kw < 0 or discharge_kw < 0:
            raise ValueError("charge_kw and discharge_kw must be non-negative")
        if charge_kw > 0 and discharge_kw > 0:
            # No simultaneous charge/discharge; prioritize larger request
            if charge_kw >= discharge_kw:
                discharge_kw = 0.0
            else:
                charge_kw = 0.0

        # Power caps
        charge_kw = min(charge_kw, self.power_kw)
        discharge_kw = min(discharge_kw, self.power_kw)

        stored_kwh = self.soc * self.capacity_kwh

        # Max charge limited by headroom
        max_store_room = (1.0 - self.soc) * self.capacity_kwh
        # Input energy delivered to battery after losses
        e_in_possible = min(charge_kw * dt_h * self.eta_chg, max_store_room)
        charge_kw_actual = e_in_possible / (dt_h * self.eta_chg) if dt_h > 0 else 0.0
        loss_chg_kwh = charge_kw_actual * dt_h - e_in_possible

        stored_kwh += e_in_possible

        # Max discharge limited by stored energy above min_soc
        max_energy_available = stored_kwh - self.min_soc * self.capacity_kwh
        max_energy_available = max(max_energy_available, 0.0)
        # Stored energy reduction corresponding to discharge output
        e_out_stored_possible = min(
            (discharge_kw * dt_h / self.eta_dis) if self.eta_dis > 0 else 0.0,
            max_energy_available,
        )
        discharge_kw_actual = e_out_stored_possible * self.eta_dis / dt_h if dt_h > 0 else 0.0
        loss_dis_kwh = e_out_stored_possible - discharge_kw_actual * dt_h

        stored_kwh -= e_out_stored_possible

        # Update SoC within bounds
        self.soc = min(1.0, max(self.min_soc, stored_kwh / self.capacity_kwh))

        return {
            "charge_kw": charge_kw_actual,
            "discharge_kw": discharge_kw_actual,
            "e_in_stored_kwh": e_in_possible,
            "e_out_stored_kwh": e_out_stored_possible,
            "loss_kwh": loss_chg_kwh + loss_dis_kwh,
            "soc": self.soc,
        }


def generate_ev_charging_profile_kw(
    *,
    minutes: int = 24 * 60,
    step_min: int = 5,
    arrival_slot: int = 19 * 60 // 5,
    energy_kwh: float = 10.0,
    circuit_kw: float = 7.2,
) -> list[float]:
    """Simple EV charging session.

    Starts at `arrival_slot`; charges at `circuit_kw` until energy is delivered.

    Capped by daily horizon.
    """
    steps = minutes // step_min
    dt_h = step_min / 60.0
    power = [0.0] * steps
    remaining = max(0.0, energy_kwh)
    for i in range(arrival_slot, steps):
        if remaining <= 0:
            break
        deliver = min(circuit_kw * dt_h, remaining)
        power[i] = deliver / dt_h
        remaining -= deliver
    return power
