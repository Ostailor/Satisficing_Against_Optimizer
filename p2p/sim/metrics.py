from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..market.order_book import Order
from ..market.order_book import Trade as TradeRec


@dataclass
class RunSummary:
    intervals: int
    agents: int
    posted_volume_kwh: float
    traded_volume_kwh: float


def compute_quote_welfare(trades: Iterable[TradeRec]) -> float:
    """Quote-based welfare: sum over trades of (bid - ask) * qty.

    Uses trade records with bid_price_cperkwh and ask_price_cperkwh.
    """
    w = 0.0
    for tr in trades:
        w += (tr.bid_price_cperkwh - tr.ask_price_cperkwh) * tr.qty_kwh
    return w


def _as_price_qty(items: Iterable[Order], side: str) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for o in items:
        if side == "buy":
            out.append((o.price_cperkwh, o.qty_kwh))
        else:
            out.append((o.price_cperkwh, o.qty_kwh))
    return out


def planner_bound_quote_welfare(
    *,
    bids: Iterable[Order],
    asks: Iterable[Order],
    feeder_limit_kw: float | None = None,
    step_min: int = 5,
) -> tuple[float, float]:
    """Greedy planner bound for quote-surplus welfare.

    - Sort bids desc by price, asks asc by price.
    - Match while bid_price >= ask_price.
    - Optional feeder_limit_kw adds an overall energy cap per interval of feeder_limit_kw * dt_h.
    Returns (welfare_bound, traded_kwh_bound).
    """
    bid_list = sorted(_as_price_qty(bids, "buy"), key=lambda x: -x[0])
    ask_list = sorted(_as_price_qty(asks, "sell"), key=lambda x: x[0])
    i = 0
    j = 0
    w_bound = 0.0
    traded = 0.0
    energy_cap = None
    if feeder_limit_kw is not None:
        energy_cap = feeder_limit_kw * (step_min / 60.0)

    while i < len(bid_list) and j < len(ask_list):
        bp, bq = bid_list[i]
        ap, aq = ask_list[j]
        if bp < ap:
            break
        # feasible trade
        qty = min(bq, aq)
        if energy_cap is not None:
            remaining = max(0.0, energy_cap - traded)
            if remaining <= 0.0:
                break
            qty = min(qty, remaining)
        w_bound += (bp - ap) * qty
        traded += qty
        bq -= qty
        aq -= qty
        if bq <= 0:
            i += 1
        else:
            bid_list[i] = (bp, bq)
        if aq <= 0:
            j += 1
        else:
            ask_list[j] = (ap, aq)

    return w_bound, traded
