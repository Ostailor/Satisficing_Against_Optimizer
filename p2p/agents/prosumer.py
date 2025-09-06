from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass
class Prosumer:
    """
    Base prosumer.

    Minimal state sufficient for smoke-run; extended in later phases.
    """

    agent_id: str
    has_battery: bool = False
    soc: float = 0.0  # state of charge [0,1]
    net_position_kwh: float = 0.0
    params: dict[str, float] = field(default_factory=dict)

    def make_quote(self, t: int) -> tuple[float, float, Side] | None:
        """Produce a minimal quote: (price c/kWh, quantity kWh, side) or None.

        Smoke-run heuristic: alternate sides and small quantities.
        """
        qty = 0.5
        if (hash(self.agent_id) + t) % 2 == 0:
            return (15.0, qty, "sell")
        return (17.0, qty, "buy")

    def decide(self, order_book_snapshot: dict, t: int) -> str:
        """Decide on action based on a snapshot. Smoke-run is idle/post only.

        Returns an action label for logging.
        """
        _ = order_book_snapshot
        return "post"
