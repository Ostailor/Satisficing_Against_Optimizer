from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

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

    bids: List[Order] = field(default_factory=list)
    asks: List[Order] = field(default_factory=list)

    def insert(self, order: Order) -> None:
        if order.side == "buy":
            self.bids.append(order)
        else:
            self.asks.append(order)

    def snapshot(self) -> Tuple[List[Order], List[Order]]:
        return list(self.bids), list(self.asks)

    def clear_all(self) -> None:
        self.bids.clear()
        self.asks.clear()

