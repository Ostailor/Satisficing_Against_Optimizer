from __future__ import annotations

from .prosumer import Prosumer


class Satisficer(Prosumer):
    """Satisficing agent placeholder with τ and K parameters.

    For smoke mode, behaviour mirrors Prosumer; τ and K added for later phases.
    """

    tau_percent: float = 5.0
    k_max: int = 3

    def decide(self, order_book_snapshot: dict, t: int) -> str:
        _ = order_book_snapshot, t
        return "post"
