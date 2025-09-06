from __future__ import annotations

from typing import Any

from .prosumer import Prosumer


class NoRegretLearner(Prosumer):
    """No-regret learner placeholder over discrete price ticks.

    Smoke-mode: behaves as Prosumer; later phases add UCB/epsilon-greedy updates.
    """

    def decide(self, order_book_snapshot: dict, t: int) -> dict[str, Any]:
        _ = order_book_snapshot, t
        return {"type": "post"}
