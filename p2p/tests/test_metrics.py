from __future__ import annotations

from p2p.market.order_book import Order, OrderBook
from p2p.sim.metrics import compute_quote_welfare, planner_bound_quote_welfare


def test_planner_bound_ge_realized() -> None:
    ob = OrderBook()
    # Two asks
    ob.submit(agent_id="s1", side="sell", price_cperkwh=15.0, qty_kwh=0.5)
    ob.submit(agent_id="s2", side="sell", price_cperkwh=16.0, qty_kwh=0.5)
    # Two bids
    ob.submit(agent_id="b1", side="buy", price_cperkwh=16.0, qty_kwh=0.6)
    ob.submit(agent_id="b2", side="buy", price_cperkwh=14.0, qty_kwh=0.6)
    # Snapshot book before clearing trades (the last submit may have matched;
    # so rebuild a fresh book)
    # Build a fresh OB without matching to compute bound
    bids = [
        Order(
            order_id=1,
            price_cperkwh=16.0,
            qty_kwh=0.6,
            side="buy",
            agent_id="b1",
            arrival_seq=0,
        )
    ]
    asks = [
        Order(
            order_id=2,
            price_cperkwh=15.0,
            qty_kwh=0.5,
            side="sell",
            agent_id="s1",
            arrival_seq=0,
        ),
        Order(
            order_id=3,
            price_cperkwh=16.0,
            qty_kwh=0.5,
            side="sell",
            agent_id="s2",
            arrival_seq=0,
        ),
    ]
    w_bound, _ = planner_bound_quote_welfare(bids=bids, asks=asks)

    # Now actually match with OB
    ob2 = OrderBook()
    for a in asks:
        ob2.submit(
            agent_id=a.agent_id,
            side=a.side,
            price_cperkwh=a.price_cperkwh,
            qty_kwh=a.qty_kwh,
        )
    for b in bids:
        ob2.submit(
            agent_id=b.agent_id,
            side=b.side,
            price_cperkwh=b.price_cperkwh,
            qty_kwh=b.qty_kwh,
        )
    trades = ob2.clear_trades()
    w_realized = compute_quote_welfare(trades)
    assert w_bound + 1e-12 >= w_realized


def test_planner_equal_on_simple_cross() -> None:
    bids = [
        Order(
            order_id=1,
            price_cperkwh=20.0,
            qty_kwh=1.0,
            side="buy",
            agent_id="b",
            arrival_seq=0,
        )
    ]
    asks = [
        Order(
            order_id=2,
            price_cperkwh=10.0,
            qty_kwh=1.0,
            side="sell",
            agent_id="s",
            arrival_seq=0,
        )
    ]
    w_bound, traded = planner_bound_quote_welfare(bids=bids, asks=asks)
    assert traded == 1.0 and abs(w_bound - (20.0 - 10.0) * 1.0) < 1e-12
