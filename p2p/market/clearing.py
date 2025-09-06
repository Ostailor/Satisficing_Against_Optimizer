from __future__ import annotations

from dataclasses import dataclass

from ..agents.prosumer import Prosumer
from .order_book import OrderBook, Trade


@dataclass
class ClearingResult:
    trades: int
    traded_kwh: float
    posted_kwh: float
    posted_buy_kwh: float
    posted_sell_kwh: float
    trades_detail: list[Trade]


def step_interval(t: int, agents: list[Prosumer], ob: OrderBook) -> ClearingResult:
    """One interval: agents submit quotes; CDA matches continuously (maker-price)."""
    posted = 0.0
    posted_buy = 0.0
    posted_sell = 0.0
    for a in agents:
        q = a.make_quote(t)
        if q is None:
            continue
        price, qty, side = q
        posted += qty
        if side == "buy":
            posted_buy += qty
        else:
            posted_sell += qty
        _order_id, _trades = ob.submit(
            agent_id=a.agent_id,
            side=side,
            price_cperkwh=price,
            qty_kwh=qty,
        )
        # Trades accumulate inside the book; we aggregate below

    interval_trades = ob.clear_trades()
    traded = sum(tr.qty_kwh for tr in interval_trades)
    return ClearingResult(
        trades=len(interval_trades),
        traded_kwh=traded,
        posted_kwh=posted,
        posted_buy_kwh=posted_buy,
        posted_sell_kwh=posted_sell,
        trades_detail=interval_trades,
    )
