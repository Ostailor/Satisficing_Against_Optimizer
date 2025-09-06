from __future__ import annotations

import argparse
import csv
import os
from contextlib import suppress
from dataclasses import asdict
from typing import Any

from ..agents.optimizer import Optimizer
from ..agents.satisficer import Satisficer
from ..agents.zi import ZIConstrained
from ..market.clearing import step_interval
from ..market.order_book import OrderBook
from .metrics import RunSummary
from .profiling import process_mem_mb, time_call


def run_smoke(
    intervals: int = 2,
    n_agents: int = 4,
    instrument: bool = False,
    metrics_out: str | None = None,
) -> RunSummary:
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
    run_id = "smoke"
    writer = None
    if instrument and metrics_out:
        os.makedirs(os.path.dirname(metrics_out) or ".", exist_ok=True)
        fh = open(metrics_out, mode="w", newline="")  # noqa: SIM115
        writer = csv.writer(fh)
        writer.writerow(
            [
                "run_id",
                "t",
                "agent_id",
                "agent_type",
                "action_type",
                "price_cperkwh",
                "qty_kwh",
                "offers_seen",
                "solver_calls",
                "learners_steps",
                "wall_ms",
                "mem_mb",
            ]
        )
    try:
        for t in range(intervals):
            # Sample process memory once per interval
            mem_mb = process_mem_mb() if instrument else 0.0
            # Snapshot for agent decisions (dict form)
            bids, asks = ob.snapshot()
            snapshot: dict[str, Any] = {"bids": bids, "asks": asks}
            if instrument and writer is not None:
                for a in agents:
                    act, wall_ms = time_call(a.decide, snapshot, t)
                    if isinstance(act, dict):
                        action_type = str(act.get("type", "none"))
                        offers_seen = int(act.get("offers_seen", 0))
                        solver_calls = int(act.get("solver_calls", 0))
                        learners_steps = int(act.get("learners_steps", 0))
                        price = act.get("price")
                        qty = act.get("qty_kwh")
                    else:
                        action_type = "none"
                        offers_seen = solver_calls = learners_steps = 0
                        price = qty = None
                    agent_type = a.__class__.__name__
                    writer.writerow(
                        [
                            run_id,
                            t,
                            a.agent_id,
                            agent_type,
                            action_type,
                            price,
                            qty,
                            offers_seen,
                            solver_calls,
                            learners_steps,
                            f"{wall_ms:.3f}",
                            f"{mem_mb:.2f}",
                        ]
                    )
            result = step_interval(t=t, agents=agents, ob=ob)
            total_posted += result.posted_kwh
            total_traded += result.traded_kwh
    finally:
        if writer is not None:
            with suppress(Exception):
                fh.close()

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
    parser.add_argument("--instrument", action="store_true", help="Enable decision instrumentation")
    parser.add_argument("--metrics-out", type=str, default="outputs/metrics_smoke.csv")
    args = parser.parse_args()

    if args.smoke:
        summary = run_smoke(
            intervals=args.intervals,
            n_agents=args.agents,
            instrument=args.instrument,
            metrics_out=args.metrics_out,
        )
        print({**asdict(summary)})
        return
    parser.error("No mode selected. Use --smoke for Phase 0.")


if __name__ == "__main__":
    main()
