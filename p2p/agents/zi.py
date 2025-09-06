from __future__ import annotations

import random

from .prosumer import Prosumer, Side


class ZIConstrained(Prosumer):
    """Zero-Intelligence Constrained baseline.

    Smoke-mode: generate random quotes within a plausible band, respecting a small qty.
    """

    def make_quote(self, t: int) -> tuple[float, float, Side] | None:
        _ = t
        price = random.uniform(10.0, 25.0)
        qty = 0.5
        side: Side = random.choice(["buy", "sell"])  # type: ignore[assignment]
        return (round(price, 1), qty, side)

    def decide(self, order_book_snapshot: dict, t: int) -> str:
        _ = order_book_snapshot, t
        return "post"
