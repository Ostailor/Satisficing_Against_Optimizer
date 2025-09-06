from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass
class Order:
    order_id: int
    price_cperkwh: float
    qty_kwh: float
    side: Side
    agent_id: str
    arrival_seq: int  # FIFO within price


@dataclass
class Trade:
    price_cperkwh: float
    qty_kwh: float
    buy_agent: str
    sell_agent: str
    maker_order_id: int
    taker_order_id: int


@dataclass
class OrderBook:
    """Price-time priority order book with maker-price matching.

    - Bids sorted by price desc, then FIFO within price.
    - Asks sorted by price asc, then FIFO within price.
    - Matching is continuous: incoming order (taker) matches resting book (maker).
    - Trade price = resting order's price (maker-price rule).
    """

    tick_cents: float = 0.1
    bids: list[Order] = field(default_factory=list)
    asks: list[Order] = field(default_factory=list)
    _id_counter: int = 0
    _arrival_counter: int = 0
    _trades: list[Trade] = field(default_factory=list)

    # ---------- Public API ----------
    def submit(
        self, *, agent_id: str, side: Side, price_cperkwh: float, qty_kwh: float
    ) -> tuple[int, list[Trade]]:
        """Submit an order and perform immediate matching.

        Returns (order_id, trades). If residual remains, it rests in the book.
        """
        if qty_kwh <= 0:
            raise ValueError("qty_kwh must be positive")
        price = self._normalize_price(price_cperkwh)
        self._id_counter += 1
        self._arrival_counter += 1
        incoming = Order(
            order_id=self._id_counter,
            price_cperkwh=price,
            qty_kwh=qty_kwh,
            side=side,
            agent_id=agent_id,
            arrival_seq=self._arrival_counter,
        )
        trades = self._match(incoming)
        # If residual remains, add to resting book
        if incoming.qty_kwh > 0:
            self._rest(incoming)
        return incoming.order_id, trades

    def cancel(self, order_id: int) -> bool:
        """Cancel a resting order by id."""
        for book in (self.bids, self.asks):
            for i, o in enumerate(book):
                if o.order_id == order_id:
                    del book[i]
                    return True
        return False

    def modify(
        self,
        order_id: int,
        *,
        new_qty_kwh: float | None = None,
        new_price_cperkwh: float | None = None,
    ) -> bool:
        """Modify a resting order. Price change resets time priority (treated as cancel + re-add).

        If new_qty_kwh <= 0, cancels the order.
        """
        # Locate order
        side: Side | None = None
        order: Order | None = None
        idx: int | None = None
        book: list[Order] | None = None
        for _bname, b in (("bids", self.bids), ("asks", self.asks)):
            for i, o in enumerate(b):
                if o.order_id == order_id:
                    side = o.side
                    order = o
                    idx = i
                    book = b
                    break
            if order is not None:
                break
        if order is None or idx is None or book is None or side is None:
            return False

        # Quantity-only change
        if new_price_cperkwh is None:
            if new_qty_kwh is None:
                return False
            if new_qty_kwh <= 0:
                del book[idx]
                return True
            order.qty_kwh = new_qty_kwh
            return True

        # Price change: cancel and resubmit at new price
        del book[idx]
        _, _ = self.submit(
            agent_id=order.agent_id,
            side=side,
            price_cperkwh=new_price_cperkwh,
            qty_kwh=new_qty_kwh if new_qty_kwh is not None else order.qty_kwh,
        )
        return True

    def best_bid(self) -> float | None:
        return self.bids[0].price_cperkwh if self.bids else None

    def best_ask(self) -> float | None:
        return self.asks[0].price_cperkwh if self.asks else None

    def snapshot(self) -> tuple[list[Order], list[Order]]:
        return list(self.bids), list(self.asks)

    def clear_trades(self) -> list[Trade]:
        out = self._trades
        self._trades = []
        return out

    # ---------- Internal helpers ----------
    def _normalize_price(self, p: float) -> float:
        if p < 0:
            raise ValueError("price must be non-negative")
        # Round to nearest tick
        tick = self.tick_cents
        return round(round(p / tick) * tick, 3)

    def _rest(self, order: Order) -> None:
        if order.side == "buy":
            self._insert_sorted(self.bids, order, reverse=True)
        else:
            self._insert_sorted(self.asks, order, reverse=False)

    @staticmethod
    def _insert_sorted(book: list[Order], order: Order, *, reverse: bool) -> None:
        # Insert maintaining price order.
        # For bids: descending price (reverse=True). For asks: ascending price.
        # FIFO is preserved within a price level.
        key_price = order.price_cperkwh
        pos = 0
        if reverse:
            # higher price first
            while pos < len(book) and (
                book[pos].price_cperkwh > key_price
                or (
                    book[pos].price_cperkwh == key_price
                    and book[pos].arrival_seq < order.arrival_seq
                )
            ):
                pos += 1
        else:
            # lower price first
            while pos < len(book) and (
                book[pos].price_cperkwh < key_price
                or (
                    book[pos].price_cperkwh == key_price
                    and book[pos].arrival_seq < order.arrival_seq
                )
            ):
                pos += 1
        book.insert(pos, order)

    def _crossing(self) -> bool:
        return bool(
            self.bids
            and self.asks
            and self.bids[0].price_cperkwh >= self.asks[0].price_cperkwh
        )

    def _match(self, incoming: Order) -> list[Trade]:
        trades: list[Trade] = []
        # Match against opposite book
        if incoming.side == "buy":
            # buy taker matches asks (makers) from lowest price
            while (
                incoming.qty_kwh > 0
                and self.asks
                and incoming.price_cperkwh >= self.asks[0].price_cperkwh
            ):
                maker = self.asks[0]
                qty = min(incoming.qty_kwh, maker.qty_kwh)
                price = maker.price_cperkwh  # maker-price rule
                trades.append(
                    Trade(
                        price_cperkwh=price,
                        qty_kwh=qty,
                        buy_agent=incoming.agent_id,
                        sell_agent=maker.agent_id,
                        maker_order_id=maker.order_id,
                        taker_order_id=incoming.order_id,
                    )
                )
                self._trades.append(trades[-1])
                incoming.qty_kwh -= qty
                maker.qty_kwh -= qty
                if maker.qty_kwh <= 0:
                    self.asks.pop(0)
        else:
            # sell taker matches bids (makers) from highest price
            while (
                incoming.qty_kwh > 0
                and self.bids
                and incoming.price_cperkwh <= self.bids[0].price_cperkwh
            ):
                maker = self.bids[0]
                qty = min(incoming.qty_kwh, maker.qty_kwh)
                price = maker.price_cperkwh  # maker-price rule
                trades.append(
                    Trade(
                        price_cperkwh=price,
                        qty_kwh=qty,
                        buy_agent=maker.agent_id,
                        sell_agent=incoming.agent_id,
                        maker_order_id=maker.order_id,
                        taker_order_id=incoming.order_id,
                    )
                )
                self._trades.append(trades[-1])
                incoming.qty_kwh -= qty
                maker.qty_kwh -= qty
                if maker.qty_kwh <= 0:
                    self.bids.pop(0)
        return trades
