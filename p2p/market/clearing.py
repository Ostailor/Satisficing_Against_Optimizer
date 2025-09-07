from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ..agents.prosumer import Prosumer, Side
from .order_book import Order, OrderBook, Trade


@dataclass
class ClearingResult:
    trades: int
    traded_kwh: float
    posted_kwh: float
    posted_buy_kwh: float
    posted_sell_kwh: float
    trades_detail: list[Trade]
    posted_bids: list[Order]
    posted_asks: list[Order]
    book_bids_start: list[Order]
    book_asks_start: list[Order]


def step_interval(t: int, agents: list[Prosumer], ob: OrderBook) -> ClearingResult:
    """One interval: agents inspect book and either accept or post; CDA matches (maker-price)."""
    posted = 0.0
    posted_buy = 0.0
    posted_sell = 0.0
    posted_bids: list[Order] = []
    posted_asks: list[Order] = []
    # Snapshot resting book at start of interval (before submissions) and deep-copy orders
    _bids0, _asks0 = ob.snapshot()
    book_bids_start = [
        Order(
            order_id=o.order_id,
            price_cperkwh=o.price_cperkwh,
            qty_kwh=o.qty_kwh,
            side=o.side,
            agent_id=o.agent_id,
            arrival_seq=o.arrival_seq,
        )
        for o in _bids0
    ]
    book_asks_start = [
        Order(
            order_id=o.order_id,
            price_cperkwh=o.price_cperkwh,
            qty_kwh=o.qty_kwh,
            side=o.side,
            agent_id=o.agent_id,
            arrival_seq=o.arrival_seq,
        )
        for o in _asks0
    ]
    for a in agents:
        # Allow accept if agent chooses
        bids0, asks0 = ob.snapshot()
        snapshot = {"bids": bids0, "asks": asks0}
        act = a.decide(snapshot, t)
        if isinstance(act, dict) and act.get("type") == "accept":
            side = cast(Side, act.get("side", "buy"))
            price = float(act.get("price", 0.0))
            qty = float(act.get("qty_kwh", 0.0))
            if qty > 0:
                _order_id, _ = ob.submit(
                    agent_id=a.agent_id, side=side, price_cperkwh=price, qty_kwh=qty
                )
                posted += qty
                if side == "buy":
                    posted_buy += qty
                    posted_bids.append(
                        Order(
                            order_id=0,
                            price_cperkwh=price,
                            qty_kwh=qty,
                            side=side,
                            agent_id=a.agent_id,
                            arrival_seq=0,
                        )
                    )
                else:
                    posted_sell += qty
                    posted_asks.append(
                        Order(
                            order_id=0,
                            price_cperkwh=price,
                            qty_kwh=qty,
                            side=side,
                            agent_id=a.agent_id,
                            arrival_seq=0,
                        )
                    )
                continue

        # Otherwise, post a fresh quote
        q = a.make_quote(t)
        if q is None:
            continue
        price, qty, side = q
        posted += qty
        if side == "buy":
            posted_buy += qty
            posted_bids.append(
                Order(
                    order_id=0,
                    price_cperkwh=price,
                    qty_kwh=qty,
                    side=side,
                    agent_id=a.agent_id,
                    arrival_seq=0,
                )
            )
        else:
            posted_sell += qty
            posted_asks.append(
                Order(
                    order_id=0,
                    price_cperkwh=price,
                    qty_kwh=qty,
                    side=side,
                    agent_id=a.agent_id,
                    arrival_seq=0,
                )
            )
        _order_id, _ = ob.submit(
            agent_id=a.agent_id, side=side, price_cperkwh=price, qty_kwh=qty
        )

    interval_trades = ob.clear_trades()
    traded = sum(tr.qty_kwh for tr in interval_trades)
    return ClearingResult(
        trades=len(interval_trades),
        traded_kwh=traded,
        posted_kwh=posted,
        posted_buy_kwh=posted_buy,
        posted_sell_kwh=posted_sell,
        trades_detail=interval_trades,
        posted_bids=posted_bids,
        posted_asks=posted_asks,
        book_bids_start=book_bids_start,
        book_asks_start=book_asks_start,
    )
