from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Literal

from ..env.devices import Battery
from ..env.params import DEFAULTS
from ..env.profiles import household_load_profile_kwh, pv_profile_kwh, sample_pv_nameplate_kw

Side = Literal["buy", "sell"]


@dataclass
class Prosumer:
    """Base prosumer with simple environment wiring (Phase 2).

    - Generates load/PV/EV profiles for a 24h horizon (5‑min steps) unless provided.
    - Computes per‑interval net position n_i(t) in kWh (positive => needs energy => buy).
    - Battery dispatch is a no‑op placeholder (neutral) for now.
    """

    agent_id: str
    step_min: int = 5
    seed: int | None = None

    # Environment profiles (kWh for load/PV per interval; kW for EV power)
    load_kwh: list[float] | None = None
    pv_kwh: list[float] | None = None
    ev_kw: list[float] | None = None

    # Devices
    battery: Battery | None = None

    # Derived/current state
    t: int = 0
    net_position_kwh: float = 0.0
    params: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Deterministic per-agent RNG (non-crypto)
        seed = self.seed if self.seed is not None else (hash(self.agent_id) & 0xFFFF)
        rng = random.Random(seed)  # noqa: S311
        steps = 24 * 60 // self.step_min
        if self.load_kwh is None:
            self.load_kwh = household_load_profile_kwh(step_min=self.step_min, rng=rng)
        if self.pv_kwh is None:
            nameplate = sample_pv_nameplate_kw(rng=rng)
            self.pv_kwh = pv_profile_kwh(nameplate_kw=nameplate, step_min=self.step_min, rng=rng)
        if self.ev_kw is None:
            # Default: no EV charging in smoke mode
            self.ev_kw = [0.0] * steps

    @property
    def dt_h(self) -> float:
        return self.step_min / 60.0

    def net_at(self, t: int) -> float:
        assert self.load_kwh is not None and self.pv_kwh is not None and self.ev_kw is not None
        ev_kwh = self.ev_kw[t] * self.dt_h
        # Neutral battery policy: no charge/discharge in Phase 2
        b_in_kwh = 0.0
        b_out_kwh = 0.0
        net = (self.load_kwh[t] + ev_kwh) - self.pv_kwh[t] - b_out_kwh + b_in_kwh
        return net

    def make_quote(self, t: int) -> tuple[float, float, Side] | None:
        """Produce a quote from net position: (price c/kWh, quantity kWh, side) or None.

        Simple heuristic pricing around retail defaults.
        """
        net = self.net_at(t)
        eps = 1e-6
        if abs(net) < eps:
            return None
        qty = abs(net)
        # Simple price anchor
        retail = DEFAULTS.get("retail_price_cperkwh", 16.3)
        price = retail + (0.5 if net > 0 else -0.5)
        side: Side = "buy" if net > 0 else "sell"
        return price, qty, side

    def decide(self, order_book_snapshot: dict, t: int) -> dict[str, Any]:
        """Decide on action based on a snapshot. Placeholder: always post."""
        _ = order_book_snapshot, t
        return {"type": "post"}
