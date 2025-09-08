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
from .metrics import RunSummary, compute_quote_welfare, planner_bound_quote_welfare
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
    interval_writer = None
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
    # Optional per-interval metrics CSV
    interval_metrics_path = os.environ.get("P2P_INTERVAL_METRICS")
    if interval_metrics_path:
        os.makedirs(os.path.dirname(interval_metrics_path) or ".", exist_ok=True)
        fh_int = open(interval_metrics_path, mode="w", newline="")  # noqa: SIM115
        interval_writer = csv.writer(fh_int)
        interval_writer.writerow(
            [
                "t",
                "trades",
                "traded_kwh",
                "posted_buy_kwh",
                "posted_sell_kwh",
                "unserved_kwh",
                "curtailment_kwh",
                "price_mean",
                "price_var",
                "W",
                "W_bound",
                "W_hat",
            ]
        )
    try:
        for t in range(intervals):
            # Sample process memory once per interval for logging
            mem_mb = process_mem_mb() if instrument else 0.0
            # Optional decision logger to avoid double decision calls
            decision_logger = None
            if instrument and writer is not None:
                def _log(a: Any, act: dict[str, Any] | Any, wall_ms: float) -> None:
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
                decision_logger = _log
            result = step_interval(t=t, agents=agents, ob=ob, decision_logger=decision_logger)
            total_posted += result.posted_kwh
            total_traded += result.traded_kwh
            if interval_writer is not None:
                prices = [tr.price_cperkwh for tr in result.trades_detail]
                price_mean = sum(prices) / len(prices) if prices else 0.0
                price_var = (
                    sum((p - price_mean) ** 2 for p in prices) / len(prices) if prices else 0.0
                )
                w = compute_quote_welfare(result.trades_detail)
                # Planner bound using the union of starting resting book and new posts
                bids_union = result.book_bids_start + result.posted_bids
                asks_union = result.book_asks_start + result.posted_asks
                w_bound, _ = planner_bound_quote_welfare(bids=bids_union, asks=asks_union)
                w_hat = (w / w_bound) if w_bound > 0 else 0.0
                # Debug: print if W_hat > 1 (should not happen)
                if w_bound > 0 and w_hat > 1.000001:
                    vol_bids0 = sum(o.qty_kwh for o in result.book_bids_start)
                    vol_asks0 = sum(o.qty_kwh for o in result.book_asks_start)
                    vol_bids_post = sum(o.qty_kwh for o in result.posted_bids)
                    vol_asks_post = sum(o.qty_kwh for o in result.posted_asks)
                    print(
                        f"[DEBUG] t={t} W={w:.6f} W_bound={w_bound:.6f} W_hat={w_hat:.6f} "
                        f"bids0={len(result.book_bids_start)}({vol_bids0:.6f}) "
                        f"postsB={len(result.posted_bids)}({vol_bids_post:.6f}) "
                        f"asks0={len(result.book_asks_start)}({vol_asks0:.6f}) "
                        f"postsA={len(result.posted_asks)}({vol_asks_post:.6f})"
                    )
                unserved = max(0.0, result.posted_buy_kwh - result.traded_kwh)
                curtail = max(0.0, result.posted_sell_kwh - result.traded_kwh)
                interval_writer.writerow(
                    [
                        t,
                        result.trades,
                        f"{result.traded_kwh:.6f}",
                        f"{result.posted_buy_kwh:.6f}",
                        f"{result.posted_sell_kwh:.6f}",
                        f"{unserved:.6f}",
                        f"{curtail:.6f}",
                        f"{price_mean:.6f}",
                        f"{price_var:.6f}",
                        f"{w:.6f}",
                        f"{w_bound:.6f}",
                        f"{w_hat:.6f}",
                    ]
                )
    finally:
        if writer is not None:
            with suppress(Exception):
                fh.close()
        if interval_writer is not None:
            with suppress(Exception):
                fh_int.close()

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
