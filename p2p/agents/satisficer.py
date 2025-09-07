from __future__ import annotations

from typing import Any, Literal

from .prosumer import Prosumer

Mode = Literal["band", "k_search", "k_greedy"]


class Satisficer(Prosumer):
    """Satisficing agent with τ-band and K-search variants.

    decide() inspects the opposite side of the book and returns a planned action:
    {"type": "accept", "order_id": int, "qty_kwh": float, "offers_seen": int} or
    {"type": "post", ...} if no acceptance is triggered.
    """

    tau_percent: float = 5.0
    k_max: int = 3
    mode: Mode = "band"

    def __init__(
        self,
        *,
        tau_percent: float | None = None,
        k_max: int | None = None,
        mode: Mode | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if tau_percent is not None:
            self.tau_percent = tau_percent
        if k_max is not None:
            self.k_max = k_max
        if mode is not None:
            self.mode = mode

    def _opposite_list(self, snapshot: Any, side: str) -> list[Any]:
        if isinstance(snapshot, dict):
            bids = snapshot.get("bids", [])
            asks = snapshot.get("asks", [])
        elif isinstance(snapshot, tuple) and len(snapshot) == 2:
            bids, asks = snapshot
        else:
            bids, asks = [], []
        # Scan in arrival order (FIFO), as expected by decision-rule tests.
        seq = list(asks if side == "buy" else bids)
        seq.sort(key=lambda o: getattr(o, "arrival_seq", 0))
        return seq

    def decide(self, order_book_snapshot: Any, t: int) -> dict[str, Any]:
        quote = self.make_quote(t)
        if quote is None:
            return {"type": "none", "offers_seen": 0}
        q_price, q_qty, side = quote
        opp = self._opposite_list(order_book_snapshot, side)

        offers_seen = 0
        if self.mode == "band":
            band = self.tau_percent / 100.0
            for o in opp:
                offers_seen += 1
                price = getattr(o, "price_cperkwh", None) or o[0]
                if q_price == 0:
                    continue
                crosses = (
                    (side == "buy" and price <= q_price)
                    or (side == "sell" and price >= q_price)
                )
                if crosses and abs(price - q_price) / q_price <= band:
                    oid = getattr(o, "order_id", None) or o[3]
                    qty = min(q_qty, getattr(o, "qty_kwh", None) or o[1])
                    return {
                        "type": "accept",
                        "order_id": oid,
                        "qty_kwh": qty,
                        "offers_seen": offers_seen,
                        "price": price,
                        "side": side,
                    }
            return {"type": "post", "offers_seen": offers_seen}

        if self.mode == "k_search":
            best = None
            k = max(1, int(self.k_max))
            for o in opp[:k]:
                offers_seen += 1
                price = getattr(o, "price_cperkwh", None) or o[0]
                oid = getattr(o, "order_id", None) or o[3]
                qty = getattr(o, "qty_kwh", None) or o[1]
                feasible = (
                    (side == "buy" and price <= q_price)
                    or (side == "sell" and price >= q_price)
                )
                if not feasible:
                    continue
                key = price if side == "buy" else -price
                if best is None or key < best[0]:
                    best = (key, price, oid, qty)
            if best is None:
                return {"type": "post", "offers_seen": offers_seen}
            _, price, oid, oqty = best
            qty = min(q_qty, oqty)
            return {
                "type": "accept",
                "order_id": oid,
                "qty_kwh": qty,
                "offers_seen": offers_seen,
                "price": price,
                "side": side,
            }

        if self.mode == "k_greedy":
            k = max(1, int(self.k_max))
            feasible_qty = 0.0
            for o in opp[:k]:
                offers_seen += 1
                price = getattr(o, "price_cperkwh", None) or o[0]
                qty = float(getattr(o, "qty_kwh", None) or o[1])
                feasible = (
                    (side == "buy" and price <= q_price)
                    or (side == "sell" and price >= q_price)
                )
                if feasible:
                    take = min(q_qty - feasible_qty, qty)
                    feasible_qty += max(0.0, take)
                    if feasible_qty >= q_qty:
                        feasible_qty = q_qty
                        break
            if feasible_qty <= 0.0:
                return {"type": "post", "offers_seen": offers_seen}
            return {
                "type": "accept",
                "qty_kwh": feasible_qty,
                "offers_seen": offers_seen,
                "price": q_price,
                "side": side,
            }

        # Default: post
        return {"type": "post", "offers_seen": offers_seen}
