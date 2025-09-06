from __future__ import annotations

from typing import Dict

from .prosumer import Prosumer


class NoRegretLearner(Prosumer):
    """No-regret learner placeholder over discrete price ticks.

    Smoke-mode: behaves as Prosumer; later phases add UCB/epsilon-greedy updates.
    """

    def decide(self, order_book_snapshot: Dict, t: int) -> str:
        _ = order_book_snapshot, t
        return "post"

