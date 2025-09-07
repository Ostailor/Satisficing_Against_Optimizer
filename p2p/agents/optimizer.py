from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from .prosumer import Prosumer

Mode = Literal["single", "greedy"]


class Optimizer(Prosumer):
    """Optimizer that scans the opposite book and chooses acceptance.

    Modes:
    - "single": pick the single best maker price (previous behavior)
    - "greedy": submit a marketable limit at the agent's quote price to fill
      across multiple makers up to `q_qty` (maker-price rule ensures pay at maker prices).
    """

    mode: Mode = "single"

    def __init__(self, *, mode: Mode | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if mode is not None:
            self.mode = mode

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
        scanned = len(opp)

        # Feasible makers under the quote limit price
        feas = []
        for o in opp:
            price = getattr(o, "price_cperkwh", None) or o[0]
            oid = getattr(o, "order_id", None) or o[3]
            qty = getattr(o, "qty_kwh", None) or o[1]
            if (side == "buy" and price <= q_price) or (side == "sell" and price >= q_price):
                feas.append((price, oid, qty))

        if not feas:
            return {"type": "post", "solver_calls": scanned}

        if self.mode == "single":
            # Choose best single maker price: min for buyer, max for seller
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
                "solver_calls": scanned,
                "side": side,
            }

        # Greedy multi-fill: submit a marketable limit at the quote price; fill up to q_qty
        total_feasible = 0.0
        for _, _, oqty in feas:
            total_feasible += float(oqty)
            if total_feasible >= q_qty:
                break
        qty = min(q_qty, total_feasible)
        if qty <= 0:
            return {"type": "post", "solver_calls": scanned}
        return {
            "type": "accept",
            # Side determines taker; price is the agent's quote (marketable limit)
            "qty_kwh": qty,
            "price": q_price,
            "solver_calls": scanned,
            "side": side,
        }
