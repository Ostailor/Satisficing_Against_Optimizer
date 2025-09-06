from __future__ import annotations

 

from .prosumer import Prosumer


class Optimizer(Prosumer):
    """Optimizer agent placeholder.

    In smoke mode, inherits Prosumer behaviour; later phases will evaluate
    feasible matches or solve a small LP/knapsack-like step.
    """

    def decide(self, order_book_snapshot: dict, t: int) -> str:
        _ = order_book_snapshot, t
        return "post"
