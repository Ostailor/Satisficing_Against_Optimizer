from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .prosumer import Prosumer


class NoRegretLearner(Prosumer):
    """Simple epsilon-greedy learner over quote price offsets.

    - Arms: price offsets (cents/kWh) applied to the agent's anchor retail price
      on the buy/sell side (positive offsets for buys, negative for sells).
    - Reward proxy: 1.0 if the chosen quote would lead to a feasible crossing
      with the current book snapshot, else 0.0. This approximates acceptance probability.
    - Decision: if feasible, accepts the best maker among feasible; otherwise posts.
    """

    epsilon: float = 0.1
    arms_cents: list[float] | None = None  # e.g., [-2,-1,0,1,2]

    # internal state
    _counts: list[int] | None = None
    _values: list[float] | None = None

    def _ensure_arms(self) -> None:
        if self.arms_cents is None:
            self.arms_cents = [-2.0, -1.0, 0.0, 1.0, 2.0]
        if (
            self._counts is None
            or self._values is None
            or len(self._counts) != len(self.arms_cents)
        ):
            self._counts = [0 for _ in self.arms_cents]
            self._values = [0.0 for _ in self.arms_cents]

    def _choose_arm(self) -> int:
        self._ensure_arms()
        assert self._counts is not None and self._values is not None and self.arms_cents is not None
        # epsilon-greedy
        if self._rng.random() < self.epsilon:
            return self._rng.randrange(len(self.arms_cents))
        # exploit
        best_idx = 0
        best_val = self._values[0]
        for i, v in enumerate(self._values):
            if v > best_val:
                best_val = v
                best_idx = i
        return best_idx

    def _update_arm(self, idx: int, reward: float) -> None:
        assert self._counts is not None and self._values is not None
        self._counts[idx] += 1
        n = self._counts[idx]
        val = self._values[idx]
        self._values[idx] = val + (reward - val) / n

    def _feasible(
        self, side: str, q_price: float, opp: Iterable[Any]
    ) -> tuple[bool, float, Any | None]:
        """Return (is_feasible, best_price, best_order)."""
        best_price = None
        best_order = None
        for o in opp:
            price = getattr(o, "price_cperkwh", None) or o[0]
            if side == "buy":
                if price <= q_price and (best_price is None or price < best_price):
                    best_price, best_order = price, o
            else:
                if price >= q_price and (best_price is None or price > best_price):
                    best_price, best_order = price, o
        return (
            best_price is not None,
            float(best_price) if best_price is not None else 0.0,
            best_order,
        )

    def decide(self, order_book_snapshot: dict, t: int) -> dict[str, Any]:
        quote = self.make_quote(t)
        if quote is None:
            return {"type": "none", "learners_steps": 0}
        anchor_price, q_qty, side = quote

        # Choose an arm (price offset) for this decision
        self._ensure_arms()
        idx = self._choose_arm()
        offset = self.arms_cents[idx] if self.arms_cents is not None else 0.0
        # Apply offset: buys push up; sells push down
        q_price = max(0.0, anchor_price + (offset if side == "buy" else -offset))

        bids = order_book_snapshot.get("bids", [])
        asks = order_book_snapshot.get("asks", [])
        opp = asks if side == "buy" else bids

        feasible, best_price, best_order = self._feasible(side, q_price, opp)
        reward = 1.0 if feasible else 0.0
        self._update_arm(idx, reward)

        if feasible and best_order is not None:
            oid = getattr(best_order, "order_id", None) or best_order[3]
            qty = min(q_qty, getattr(best_order, "qty_kwh", None) or best_order[1])
            return {
                "type": "accept",
                "order_id": oid,
                "qty_kwh": qty,
                "price": best_price,
                "side": side,
                "learners_steps": 1,
            }
        return {"type": "post", "learners_steps": 1}
