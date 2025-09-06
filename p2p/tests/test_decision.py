from __future__ import annotations

from p2p.agents.optimizer import Optimizer
from p2p.agents.satisficer import Satisficer
from p2p.market.order_book import OrderBook


def _snapshot(ob: OrderBook) -> dict:
    bids, asks = ob.snapshot()
    return {"bids": bids, "asks": asks}


def test_satisficer_band_accepts_within_tau_and_stops() -> None:
    # Buyer with quote price 20; band 5% => accept if ask within [19,21]
    s = Satisficer(agent_id="a1")
    s.make_quote = lambda t: (20.0, 1.0, "buy")  # type: ignore[method-assign]
    ob = OrderBook()
    # First ask at 22 (outside band), second at 20.5 (inside)
    ob.submit(agent_id="s1", side="sell", price_cperkwh=22.0, qty_kwh=1.0)
    a2, _ = ob.submit(agent_id="s2", side="sell", price_cperkwh=20.5, qty_kwh=1.0)
    act = s.decide(_snapshot(ob), t=0)
    # Arrival order: 22 first (outside band), then 20.5 (inside) -> offers_seen=2
    assert act["type"] == "accept" and act["order_id"] == a2 and act["offers_seen"] == 2


def test_satisficer_k_search_stops_at_k_and_picks_best_among_seen() -> None:
    # Buyer with quote price high enough to cross all asks; K=2 so only first two considered
    s = Satisficer(agent_id="a2", mode="k_search", k_max=2)
    s.make_quote = lambda t: (50.0, 1.0, "buy")  # type: ignore[method-assign]
    ob = OrderBook()
    a1, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=30.0, qty_kwh=1.0)
    a2, _ = ob.submit(agent_id="s2", side="sell", price_cperkwh=25.0, qty_kwh=1.0)
    a3, _ = ob.submit(agent_id="s3", side="sell", price_cperkwh=10.0, qty_kwh=1.0)
    act = s.decide(_snapshot(ob), t=0)
    # Best among first two is a2 at 25 (a3 at 10 is ignored due to K)
    assert act["type"] == "accept" and act["order_id"] == a2 and act["offers_seen"] == 2


def test_optimizer_weakly_dominates_satisficer_price_choice() -> None:
    # Buyer case: optimizer should pick the lowest ask among feasible (<= quote)
    s = Satisficer(agent_id="a3", mode="k_search", k_max=1)
    s.make_quote = lambda t: (50.0, 1.0, "buy")  # type: ignore[method-assign]
    o = Optimizer(agent_id="o1")
    o.make_quote = s.make_quote  # type: ignore[method-assign]
    ob = OrderBook()
    a1, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=40.0, qty_kwh=1.0)
    a2, _ = ob.submit(agent_id="s2", side="sell", price_cperkwh=20.0, qty_kwh=1.0)
    snap = _snapshot(ob)
    act_s = s.decide(snap, t=0)
    act_o = o.decide(snap, t=0)
    # Optimizer price should be <= satisficer price (weak dominance)
    assert act_s["type"] == "accept" and act_o["type"] == "accept"
    assert act_o["price"] <= act_s["price"]
