from __future__ import annotations

from dataclasses import dataclass

from ..agents.prosumer import Prosumer
from .order_book import Order, OrderBook


@dataclass
class ClearingResult:
    trades: int
    volume_kwh: float


def step_interval(t: int, agents: list[Prosumer], ob: OrderBook) -> ClearingResult:
    """Smoke-mode interval step: collect quotes and do no-op matching.

    Later phases: price-time priority matching with maker-price rule.
    """
    # Agents post one quote each
    for a in agents:
        q = a.make_quote(t)
        if q is None:
            continue
        price, qty, side = q
        ob.insert(Order(price_cperkwh=price, qty_kwh=qty, side=side, agent_id=a.agent_id, ts=t))

    # No matching in smoke; just clear the book for the next interval
    bids, asks = ob.snapshot()
    volume = sum(o.qty_kwh for o in bids + asks)
    ob.clear_all()
    return ClearingResult(trades=0, volume_kwh=volume)
