from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast

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


def step_interval(
    t: int,
    agents: list[Prosumer],
    ob: OrderBook,
    *,
    info_set: str = "book",
    decision_logger: Callable[[Prosumer, dict[str, Any] | Any, float], None] | None = None,
) -> ClearingResult:
    """One interval: agents inspect book and either accept or post; CDA matches (maker-price).

    - If `decision_logger` is provided, this function will time and log each agent's
      decide() call via the callback and reuse that action (no second decide()).
    - `info_set`: 'book' for full book snapshots or 'ticker' for top-of-book only.
    """
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
        # Build snapshot per info set
        bids0, asks0 = ob.snapshot()
        snapshot = (
            {"bids": bids0[:1], "asks": asks0[:1]}
            if info_set == "ticker"
            else {"bids": bids0, "asks": asks0}
        )
        # Decide once; optionally time and log via callback
        if decision_logger is not None:
            from ..sim.profiling import time_call

            act, wall_ms = time_call(a.decide, snapshot, t)
            decision_logger(a, act, wall_ms)
        else:
            act = a.decide(snapshot, t)
        # Allow accept if agent chooses
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


def _sort_bids(b: list[Order]) -> list[Order]:
    # price desc, FIFO within price by arrival_seq
    return sorted(b, key=lambda o: (-o.price_cperkwh, o.arrival_seq))


def _sort_asks(a: list[Order]) -> list[Order]:
    # price asc, FIFO within price
    return sorted(a, key=lambda o: (o.price_cperkwh, o.arrival_seq))


def _batch_match(
    bids: list[Order],
    asks: list[Order],
    *,
    feeder_limit_kw: float | None = None,
    step_min: int = 5,
) -> tuple[list[Trade], list[Order], list[Order]]:
    """Greedy batch match by price-time priority; maker-price rule.

    Returns (trades, residual_bids, residual_asks).
    """
    b = _sort_bids(list(bids))
    a = _sort_asks(list(asks))
    trades: list[Trade] = []
    i = 0
    j = 0
    traded_kwh = 0.0
    cap_kwh = None
    if feeder_limit_kw is not None:
        cap_kwh = feeder_limit_kw * (step_min / 60.0)
    while i < len(b) and j < len(a):
        bb = b[i]
        aa = a[j]
        if bb.price_cperkwh < aa.price_cperkwh:
            break
        qty = min(bb.qty_kwh, aa.qty_kwh)
        if cap_kwh is not None:
            remaining = max(0.0, cap_kwh - traded_kwh)
            if remaining <= 0:
                break
            qty = min(qty, remaining)
        if qty <= 0:
            break
        # Trade at maker (resting) price: we take the ask's price if pairing buyer to seller
        price = aa.price_cperkwh
        trades.append(
            Trade(
                price_cperkwh=price,
                qty_kwh=qty,
                buy_agent=bb.agent_id,
                sell_agent=aa.agent_id,
                maker_order_id=aa.order_id,
                taker_order_id=bb.order_id,
                bid_price_cperkwh=bb.price_cperkwh,
                ask_price_cperkwh=aa.price_cperkwh,
            )
        )
        traded_kwh += qty
        bb.qty_kwh -= qty
        aa.qty_kwh -= qty
        if bb.qty_kwh <= 0:
            i += 1
        if aa.qty_kwh <= 0:
            j += 1
    # Residuals: keep positive-qty orders
    residual_b = [o for o in b[i:] if o.qty_kwh > 0] + [o for o in b[:i] if o.qty_kwh > 0]
    residual_a = [o for o in a[j:] if o.qty_kwh > 0] + [o for o in a[:j] if o.qty_kwh > 0]
    # Ensure sorted
    residual_b = _sort_bids(residual_b)
    residual_a = _sort_asks(residual_a)
    return trades, residual_b, residual_a


def step_interval_call(
    t: int,
    agents: list[Prosumer],
    ob: OrderBook,
    *,
    info_set: str = "book",
    decision_logger: Callable[[Prosumer, dict[str, Any] | Any, float], None] | None = None,
    feeder_limit_kw: float | None = None,
) -> ClearingResult:
    """Periodic call auction variant: collect actions, then batch match once per interval.

    - Uses price-time priority within the batch; maker-price rule.
    - Optionally enforces a feeder capacity cap (kW) converted to kWh for the interval.
    - `info_set`: 'book' (full book) or 'ticker' (top-of-book only).
    """
    posted = 0.0
    posted_buy = 0.0
    posted_sell = 0.0
    posted_bids: list[Order] = []
    posted_asks: list[Order] = []

    # Snapshot starting resting book
    bids0, asks0 = ob.snapshot()
    book_bids_start = [
        Order(
            order_id=o.order_id,
            price_cperkwh=o.price_cperkwh,
            qty_kwh=o.qty_kwh,
            side=o.side,
            agent_id=o.agent_id,
            arrival_seq=o.arrival_seq,
        )
        for o in bids0
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
        for o in asks0
    ]

    # Assign arrival_seq to new posts after existing max
    next_seq = max([o.arrival_seq for o in bids0 + asks0] + [0]) + 1

    for a in agents:
        # information set
        b, k = ob.snapshot()
        snap = {"bids": b[:1], "asks": k[:1]} if info_set == "ticker" else {"bids": b, "asks": k}
        # Decide once; optionally time/log and reuse action
        if decision_logger is not None:
            from ..sim.profiling import time_call

            act, wall_ms = time_call(a.decide, snap, t)
            decision_logger(a, act, wall_ms)
        else:
            act = a.decide(snap, t)
        # In a call auction, treat accept as a post (marketable limit) to be cleared in batch.
        if isinstance(act, dict) and act.get("type") in {"accept", "post"}:
            price = float(act.get("price") or 0.0)
            qty = float(act.get("qty_kwh") or 0.0)
            side = str(act.get("side") or (a.make_quote(t) or (0.0, 0.0, "buy"))[2])
            # If no qty in accept/post, fall back to quote
            if qty <= 0:
                q = a.make_quote(t)
                if q is None:
                    continue
                price, qty, side = q
            order = Order(
                order_id=0,
                price_cperkwh=price,
                qty_kwh=qty,
                side=side,  # type: ignore[arg-type]
                agent_id=a.agent_id,
                arrival_seq=next_seq,
            )
            next_seq += 1
            posted += qty
            if side == "buy":
                posted_buy += qty
                posted_bids.append(order)
            else:
                posted_sell += qty
                posted_asks.append(order)

    # Union and batch match once
    union_bids = book_bids_start + posted_bids
    union_asks = book_asks_start + posted_asks
    # Important: match on copies so book_bids_start/posted_* remain immutable for metrics.
    union_bids_copy = [
        Order(
            order_id=o.order_id,
            price_cperkwh=o.price_cperkwh,
            qty_kwh=o.qty_kwh,
            side=o.side,
            agent_id=o.agent_id,
            arrival_seq=o.arrival_seq,
        )
        for o in union_bids
    ]
    union_asks_copy = [
        Order(
            order_id=o.order_id,
            price_cperkwh=o.price_cperkwh,
            qty_kwh=o.qty_kwh,
            side=o.side,
            agent_id=o.agent_id,
            arrival_seq=o.arrival_seq,
        )
        for o in union_asks
    ]
    trades, residual_bids, residual_asks = _batch_match(
        union_bids_copy, union_asks_copy, feeder_limit_kw=feeder_limit_kw
    )

    # Update OB state for next interval
    ob.bids = residual_bids
    ob.asks = residual_asks
    # Report
    traded = sum(tr.qty_kwh for tr in trades)
    return ClearingResult(
        trades=len(trades),
        traded_kwh=traded,
        posted_kwh=posted,
        posted_buy_kwh=posted_buy,
        posted_sell_kwh=posted_sell,
        trades_detail=trades,
        posted_bids=posted_bids,
        posted_asks=posted_asks,
        book_bids_start=book_bids_start,
        book_asks_start=book_asks_start,
    )
