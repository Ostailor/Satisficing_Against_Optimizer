from __future__ import annotations

import random
from typing import Any

from .prosumer import Prosumer, Side


class ZIConstrained(Prosumer):
    """Zero-Intelligence Constrained baseline.

    Smoke-mode: generate random quotes within a plausible band, respecting a small qty.
    """

    def make_quote(self, t: int) -> tuple[float, float, Side] | None:
        _ = t
        price = random.uniform(10.0, 25.0)
        qty = 0.5
        choices: tuple[Side, Side] = ("buy", "sell")
        side: Side = random.choice(choices)
        return (round(price, 1), qty, side)

    def decide(self, order_book_snapshot: dict, t: int) -> dict[str, Any]:
        _ = order_book_snapshot, t
        return {"type": "post"}
