from __future__ import annotations

import argparse
from dataclasses import asdict

from ..agents.optimizer import Optimizer
from ..agents.satisficer import Satisficer
from ..agents.zi import ZIConstrained
from ..market.clearing import step_interval
from ..market.order_book import OrderBook
from .metrics import RunSummary


def run_smoke(intervals: int = 2, n_agents: int = 4) -> RunSummary:
    """Run a toy 2-interval simulation with 4 agents to verify wiring.

    Posts quotes and matches continuously via CDA; returns a summary.
    """
    agents: list = []
    # Mix of agent types
    for i in range(n_agents):
        if i % 3 == 0:
            agents.append(Optimizer(agent_id=f"opt_{i}"))
        elif i % 3 == 1:
            agents.append(Satisficer(agent_id=f"sat_{i}",))
        else:
            agents.append(ZIConstrained(agent_id=f"zi_{i}"))

    ob = OrderBook()
    total_posted = 0.0
    total_traded = 0.0
    for t in range(intervals):
        result = step_interval(t=t, agents=agents, ob=ob)
        total_posted += result.posted_kwh
        total_traded += result.traded_kwh

    return RunSummary(
        intervals=intervals,
        agents=len(agents),
        posted_volume_kwh=total_posted,
        traded_volume_kwh=total_traded,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="P2P market simulator runner")
    parser.add_argument("--smoke", action="store_true", help="Run a toy smoke simulation")
    parser.add_argument("--intervals", type=int, default=2)
    parser.add_argument("--agents", type=int, default=4)
    args = parser.parse_args()

    if args.smoke:
        summary = run_smoke(intervals=args.intervals, n_agents=args.agents)
        print({**asdict(summary)})
        return
    parser.error("No mode selected. Use --smoke for Phase 0.")


if __name__ == "__main__":
    main()
