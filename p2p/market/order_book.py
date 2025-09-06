from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass
class Order:
    price_cperkwh: float
    qty_kwh: float
    side: Side
    agent_id: str
    ts: int


@dataclass
class OrderBook:
    """Minimal order book for smoke-run.

    Maintains lists only; no matching here. Later phases implement price-time priority queues.
    """

    bids: list[Order] = field(default_factory=list)
    asks: list[Order] = field(default_factory=list)

    def insert(self, order: Order) -> None:
        if order.side == "buy":
            self.bids.append(order)
        else:
            self.asks.append(order)

    def snapshot(self) -> tuple[list[Order], list[Order]]:
        return list(self.bids), list(self.asks)

    def clear_all(self) -> None:
        self.bids.clear()
        self.asks.clear()
