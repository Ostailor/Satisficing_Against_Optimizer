from __future__ import annotations

from p2p.market.order_book import OrderBook


def test_crossing_maker_price_buy_takes_resting_ask() -> None:
    ob = OrderBook()
    # Resting ask, then incoming buy crosses
    ask_id, trades0 = ob.submit(agent_id="s1", side="sell", price_cperkwh=15.0, qty_kwh=1.0)
    assert trades0 == []
    bid_id, trades = ob.submit(agent_id="b1", side="buy", price_cperkwh=17.0, qty_kwh=1.0)
    assert len(trades) == 1
    t = trades[0]
    assert t.price_cperkwh == 15.0  # maker (resting ask) price
    assert t.qty_kwh == 1.0
    assert t.maker_order_id == ask_id
    assert t.taker_order_id == bid_id


def test_crossing_maker_price_sell_takes_resting_bid() -> None:
    ob = OrderBook()
    bid_id, trades0 = ob.submit(agent_id="b1", side="buy", price_cperkwh=17.0, qty_kwh=1.0)
    assert trades0 == []
    ask_id, trades = ob.submit(agent_id="s1", side="sell", price_cperkwh=15.0, qty_kwh=1.0)
    assert len(trades) == 1
    t = trades[0]
    assert t.price_cperkwh == 17.0  # maker (resting bid) price
    assert t.maker_order_id == bid_id
    assert t.taker_order_id == ask_id


def test_partial_fill_fifo_and_prices() -> None:
    ob = OrderBook()
    # Two resting asks at 15 and 16, FIFO within same price would apply; here distinct prices
    a1, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=15.0, qty_kwh=0.5)
    a2, _ = ob.submit(agent_id="s2", side="sell", price_cperkwh=16.0, qty_kwh=0.5)
    _, trades = ob.submit(agent_id="b1", side="buy", price_cperkwh=17.0, qty_kwh=0.7)
    assert len(trades) == 2
    # First trade at 15 (maker a1), then at 16 (maker a2)
    assert trades[0].price_cperkwh == 15.0 and trades[0].qty_kwh == 0.5
    assert trades[1].price_cperkwh == 16.0 and abs(trades[1].qty_kwh - 0.2) < 1e-9
    # Remaining ask a2 has 0.3 left
    bids, asks = ob.snapshot()
    assert len(asks) == 1 and asks[0].order_id == a2 and abs(asks[0].qty_kwh - 0.3) < 1e-9


def test_empty_book_no_trades() -> None:
    ob = OrderBook()
    _id, trades = ob.submit(agent_id="b1", side="buy", price_cperkwh=10.0, qty_kwh=1.0)
    assert trades == []
    # No crossing with higher ask
    _id, trades = ob.submit(agent_id="s1", side="sell", price_cperkwh=20.0, qty_kwh=1.0)
    assert trades == []


def test_cancel_and_modify() -> None:
    ob = OrderBook()
    oid, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=18.0, qty_kwh=1.0)
    assert ob.best_ask() == 18.0
    # Modify price down to 16 resets priority but we have single order
    assert ob.modify(oid, new_price_cperkwh=16.0)
    assert ob.best_ask() == 16.0
    # Modify quantity lower
    bids, asks = ob.snapshot()
    assert len(asks) == 1
    current_id = asks[0].order_id
    assert ob.modify(current_id, new_qty_kwh=0.4)
    bids, asks = ob.snapshot()
    assert abs(asks[0].qty_kwh - 0.4) < 1e-9
    # Cancel
    assert ob.cancel(asks[0].order_id)
    bids, asks = ob.snapshot()
    assert len(asks) == 0 and len(bids) == 0


def test_conservation_of_energy_traded() -> None:
    ob = OrderBook()
    # Total sell volume 1.0, buy volume 0.7 -> trades must be 0.7
    _a1, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=15.0, qty_kwh=0.4)
    _a2, _ = ob.submit(agent_id="s2", side="sell", price_cperkwh=16.0, qty_kwh=0.6)
    _, trades = ob.submit(agent_id="b1", side="buy", price_cperkwh=20.0, qty_kwh=0.7)
    traded = sum(t.qty_kwh for t in trades)
    assert abs(traded - 0.7) < 1e-9


def test_fifo_within_equal_price_levels() -> None:
    ob = OrderBook()
    # Two asks at the same price 15.0; s1 arrives before s2
    a1, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=15.0, qty_kwh=0.4)
    a2, _ = ob.submit(agent_id="s2", side="sell", price_cperkwh=15.0, qty_kwh=0.4)
    _, trades = ob.submit(agent_id="b1", side="buy", price_cperkwh=20.0, qty_kwh=0.5)
    # Expect first fill against s1 entirely, then partial against s2
    assert len(trades) == 2
    assert trades[0].maker_order_id == a1 and abs(trades[0].qty_kwh - 0.4) < 1e-9
    assert trades[1].maker_order_id == a2 and abs(trades[1].qty_kwh - 0.1) < 1e-9
    # Remaining ask should be s2 with 0.3 left
    _bids, asks = ob.snapshot()
    assert len(asks) == 1 and asks[0].order_id == a2 and abs(asks[0].qty_kwh - 0.3) < 1e-9


def test_tick_rounding_and_crossing() -> None:
    ob = OrderBook()
    # Ask at 15.06 rounds to 15.1
    a_id, _ = ob.submit(agent_id="s1", side="sell", price_cperkwh=15.06, qty_kwh=0.2)
    assert ob.best_ask() == 15.1
    # Buy at 15.04 rounds to 15.0 -> no crossing yet
    _b_id, trades0 = ob.submit(agent_id="b0", side="buy", price_cperkwh=15.04, qty_kwh=0.1)
    assert trades0 == [] and ob.best_bid() == 15.0
    # Buy at 15.06 rounds to 15.1 -> crosses and executes at maker (ask) price 15.1
    _b1, trades = ob.submit(agent_id="b1", side="buy", price_cperkwh=15.06, qty_kwh=0.2)
    assert len(trades) == 1
    t = trades[0]
    assert t.maker_order_id == a_id and t.price_cperkwh == 15.1 and abs(t.qty_kwh - 0.2) < 1e-9
