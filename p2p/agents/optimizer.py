from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .prosumer import Prosumer


class Optimizer(Prosumer):
    """Optimizer that evaluates all feasible counter-offers and picks the best price."""

    def _extract_opposite(self, snapshot: Any, side: str) -> Iterable[Any]:
        if isinstance(snapshot, dict):
            bids = snapshot.get("bids", [])
            asks = snapshot.get("asks", [])
        elif isinstance(snapshot, tuple) and len(snapshot) == 2:
            bids, asks = snapshot
        else:
            bids, asks = [], []
        return asks if side == "buy" else bids

    def decide(self, order_book_snapshot: Any, t: int) -> dict[str, Any]:
        quote = self.make_quote(t)
        if quote is None:
            return {"type": "none", "solver_calls": 0}
        q_price, q_qty, side = quote
        opp = list(self._extract_opposite(order_book_snapshot, side))

        # Feasible: prices that cross the quote
        feas = []
        for o in opp:
            price = getattr(o, "price_cperkwh", None) or o[0]
            oid = getattr(o, "order_id", None) or o[3]
            qty = getattr(o, "qty_kwh", None) or o[1]
            if (side == "buy" and price <= q_price) or (side == "sell" and price >= q_price):
                feas.append((price, oid, qty))

        if not feas:
            return {"type": "post", "solver_calls": 0}

        # Choose best price: min price for buyers, max for sellers
        if side == "buy":
            price, oid, oqty = min(feas, key=lambda x: x[0])
        else:
            price, oid, oqty = max(feas, key=lambda x: x[0])
        qty = min(q_qty, oqty)
        return {
            "type": "accept",
            "order_id": oid,
            "qty_kwh": qty,
            "price": price,
            "solver_calls": 1,
        }
