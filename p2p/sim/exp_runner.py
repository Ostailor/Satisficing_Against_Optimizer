from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
from datetime import datetime
from typing import Any, cast

from ..agents.optimizer import Mode as OptMode
from ..agents.optimizer import Optimizer
from ..agents.satisficer import Mode as SatMode
from ..agents.satisficer import Satisficer
from ..agents.zi import ZIConstrained
from ..market.clearing import step_interval, step_interval_call
from ..market.order_book import OrderBook
from .metrics import compute_quote_welfare, planner_bound_quote_welfare
from .profiling import process_mem_mb, time_call


def parse_int_list(arg: str) -> list[int]:
    return [int(x) for x in arg.split(",") if x]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def build_agents(
    agent: str,
    n: int,
    *,
    mode: str | None,
    tau: int | None,
    k: int | None,
    seed: int,
    price_sigma: float | None = None,
    buy_markup: float | None = None,
    sell_discount: float | None = None,
    optimizer_mode: str | None = None,
    hetero_tau: list[int] | None = None,
    hetero_k: list[int] | None = None,
) -> list:
    agents: list = []
    for i in range(n):
        aseed = (seed * 1000003 + i) & 0x7FFFFFFF
        aid = f"{agent}_{i}"
        if agent == "optimizer":
            agents.append(
                Optimizer(
                    agent_id=aid,
                    seed=aseed,
                    mode=cast(OptMode, optimizer_mode or "greedy"),
                    quote_sigma_cents=price_sigma or 0.5,
                    buy_markup_cents=buy_markup,
                    sell_discount_cents=sell_discount,
                )
            )
        elif agent == "satisficer":
            if not mode:
                raise ValueError("mode is required for satisficer: band|k_search|k_greedy")
            if mode == "band":
                if tau is None and not hetero_tau:
                    raise ValueError("tau or --hetero-tau must be provided for mode=band")
                agents.append(
                    Satisficer(
                        agent_id=aid,
                        seed=aseed,
                        mode="band",
                        tau_percent=float(
                            hetero_tau[(i % len(hetero_tau))] if hetero_tau else (tau or 5)
                        ),
                        quote_sigma_cents=price_sigma or 0.5,
                        buy_markup_cents=buy_markup,
                        sell_discount_cents=sell_discount,
                    )
                )
            elif mode in ("k_search", "k_greedy"):
                if k is None and not hetero_k:
                    raise ValueError("K or --hetero-K must be provided for mode=k_search/k_greedy")
                agents.append(
                    Satisficer(
                        agent_id=aid,
                        seed=aseed,
                        mode=cast(SatMode, mode),
                        k_max=int(hetero_k[(i % len(hetero_k))] if hetero_k else (k or 1)),
                        quote_sigma_cents=price_sigma or 0.5,
                        buy_markup_cents=buy_markup,
                        sell_discount_cents=sell_discount,
                    )
                )
            else:
                raise ValueError(f"unknown mode: {mode}")
        elif agent == "zi":
            agents.append(ZIConstrained(agent_id=aid))
        elif agent == "learner":
            from ..agents.learner import NoRegretLearner
            agents.append(
                NoRegretLearner(
                    agent_id=aid,
                    seed=aseed,
                    quote_sigma_cents=price_sigma or 0.5,
                    buy_markup_cents=buy_markup,
                    sell_discount_cents=sell_discount,
                )
            )
        else:
            raise ValueError(f"unknown agent type: {agent}")
    return agents


def run_cell(
    *,
    n: int,
    agent: str,
    mode: str | None,
    tau: int | None,
    k: int | None,
    intervals: int,
    seed: int,
    instrument_decisions: bool,
    out_dir: str,
    price_sigma: float | None = None,
    buy_markup: float | None = None,
    sell_discount: float | None = None,
    optimizer_mode: str | None = None,
    mechanism: str = "cda",
    feeder_cap: float | None = None,
    info_set: str = "book",
    hetero_tau: list[int] | None = None,
    hetero_k: list[int] | None = None,
) -> dict[str, Any]:
    # Build agents and order book
    agents = build_agents(
        agent,
        n,
        mode=mode,
        tau=tau,
        k=k,
        seed=seed,
        price_sigma=price_sigma,
        buy_markup=buy_markup,
        sell_discount=sell_discount,
        optimizer_mode=optimizer_mode,
        hetero_tau=hetero_tau,
        hetero_k=hetero_k,
    )
    ob = OrderBook()

    # Writers
    ensure_dir(out_dir)
    interval_path = os.path.join(
        out_dir,
        f"interval_metrics_N{n}_{agent}_{mode or 'na'}_tau{tau}_K{k}_s{seed}.csv",
    )
    dec_path = os.path.join(
        out_dir,
        f"decision_metrics_N{n}_{agent}_{mode or 'na'}_tau{tau}_K{k}_s{seed}.csv",
    )

    total_posted = 0.0
    total_traded = 0.0
    with open(interval_path, mode="w", newline="") as iw:
        iwriter = csv.writer(iw)
        iwriter.writerow(
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
        if instrument_decisions:
            with open(dec_path, mode="w", newline="") as dw:
                dwriter = csv.writer(dw)
                dwriter.writerow(
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
                for t in range(intervals):
                    # Snapshot and per-agent decision instrumentation
                    bids0, asks0 = ob.snapshot()
                    snapshot = (
                        {"bids": bids0[:1], "asks": asks0[:1]}
                        if info_set == "ticker"
                        else {"bids": bids0, "asks": asks0}
                    )
                    mem_mb = process_mem_mb()
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
                            offers_seen = 0
                            solver_calls = 0
                            learners_steps = 0
                            price = None
                            qty = None
                        dwriter.writerow(
                            [
                                "cell",
                                t,
                                a.agent_id,
                                a.__class__.__name__,
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
                    # Market step
                    if mechanism == "call":
                        result = step_interval_call(
                            t=t,
                            agents=agents,
                            ob=ob,
                            info_set=info_set,
                            feeder_limit_kw=feeder_cap,
                        )
                    else:
                        result = step_interval(t=t, agents=agents, ob=ob)
                    total_posted += result.posted_kwh
                    total_traded += result.traded_kwh
                    prices = [tr.price_cperkwh for tr in result.trades_detail]
                    price_mean = sum(prices) / len(prices) if prices else 0.0
                    price_var = (
                        sum((p - price_mean) ** 2 for p in prices) / len(prices) if prices else 0.0
                    )
                    welfare = compute_quote_welfare(result.trades_detail)
                    bids_union = result.book_bids_start + result.posted_bids
                    asks_union = result.book_asks_start + result.posted_asks
                    w_bound, _ = planner_bound_quote_welfare(bids=bids_union, asks=asks_union)
                    w_hat = (welfare / w_bound) if w_bound > 0 else 0.0
                    unserved = max(0.0, result.posted_buy_kwh - result.traded_kwh)
                    curtail = max(0.0, result.posted_sell_kwh - result.traded_kwh)
                    iwriter.writerow(
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
                            f"{welfare:.6f}",
                            f"{w_bound:.6f}",
                            f"{w_hat:.6f}",
                        ]
                    )
        else:
            for t in range(intervals):
                if mechanism == "call":
                    result = step_interval_call(
                        t=t,
                        agents=agents,
                        ob=ob,
                        info_set=info_set,
                        feeder_limit_kw=feeder_cap,
                    )
                else:
                    result = step_interval(t=t, agents=agents, ob=ob)
                total_posted += result.posted_kwh
                total_traded += result.traded_kwh
                prices = [tr.price_cperkwh for tr in result.trades_detail]
                price_mean = sum(prices) / len(prices) if prices else 0.0
                price_var = (
                    sum((p - price_mean) ** 2 for p in prices) / len(prices) if prices else 0.0
                )
                welfare = compute_quote_welfare(result.trades_detail)
                bids_union = result.book_bids_start + result.posted_bids
                asks_union = result.book_asks_start + result.posted_asks
                w_bound, _ = planner_bound_quote_welfare(bids=bids_union, asks=asks_union)
                w_hat = (welfare / w_bound) if w_bound > 0 else 0.0
                unserved = max(0.0, result.posted_buy_kwh - result.traded_kwh)
                curtail = max(0.0, result.posted_sell_kwh - result.traded_kwh)
                iwriter.writerow(
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
                        f"{welfare:.6f}",
                        f"{w_bound:.6f}",
                        f"{w_hat:.6f}",
                    ]
                )

    # Aggregate per-run
    agg = {
        "N": n,
        "agent": agent,
        "mode": mode,
        "tau": tau,
        "K": k,
        "seed": seed,
        "intervals": intervals,
        "posted_kwh": total_posted,
        "traded_kwh": total_traded,
        "interval_csv": interval_path,
        "decision_csv": dec_path if instrument_decisions else None,
        "mechanism": mechanism,
        "feeder_cap_kw": feeder_cap,
        "info_set": info_set,
    }
    return agg


def write_manifest(out_dir: str, config: dict[str, Any], runs: list[dict[str, Any]]) -> None:
    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    manifest = {"config": config, "env": env, "runs": runs}
    ensure_dir(out_dir)
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment runner: sweep N, tau, K, seeds")
    # Allow learner baseline via CLI in addition to optimizer/satisficer/zi
    p.add_argument("--agent", choices=["optimizer", "satisficer", "zi", "learner"], required=True)
    p.add_argument("--mode", choices=["band", "k_search", "k_greedy"], help="Satisficer mode")
    p.add_argument("--N", required=True, help="Comma-separated list of N values")
    p.add_argument("--tau", help="Comma-separated tau values (percent) for mode=band")
    p.add_argument("--K", help="Comma-separated K values for mode=k_search")
    p.add_argument("--seeds", type=int, default=5, help="Number of seeds per cell")
    p.add_argument("--intervals", type=int, default=12, help="Number of intervals (5-min steps)")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--instrument-decisions", action="store_true")
    p.add_argument(
        "--mechanism",
        choices=["cda", "call"],
        default="cda",
        help=(
            "Market mechanism: continuous double auction (cda) or periodic call auction (call)"
        ),
    )
    p.add_argument(
        "--feeder-cap",
        type=float,
        default=None,
        help="Optional feeder capacity cap in kW (applied in call auction)",
    )
    p.add_argument(
        "--info-set",
        choices=["book", "ticker"],
        default="book",
        help="Information set provided to agents",
    )
    p.add_argument(
        "--hetero-tau",
        help="Comma-separated tau values to sample per agent (band mode)",
    )
    p.add_argument(
        "--hetero-K",
        help="Comma-separated K values to sample per agent (k modes)",
    )
    p.add_argument(
        "--price-sigma",
        type=float,
        default=0.5,
        help="Per-interval quote noise (cents)",
    )
    p.add_argument("--buy-markup", type=float, help="Mean buy markup over retail (cents)")
    p.add_argument("--sell-discount", type=float, help="Mean sell discount below retail (cents)")
    p.add_argument(
        "--optimizer-mode",
        choices=["single", "greedy"],
        default="greedy",
        help="Optimizer decision mode",
    )
    args = p.parse_args()

    ns = parse_int_list(args.N)
    taus = parse_int_list(args.tau) if args.tau else []
    ks = parse_int_list(args.K) if args.K else []
    hetero_tau = parse_int_list(args.hetero_tau) if getattr(args, "hetero_tau", None) else None
    hetero_k = parse_int_list(args.hetero_K) if getattr(args, "hetero_K", None) else None

    # Determine grid based on mode/agent
    grid: list[tuple[int, int | None, int | None]]
    if args.agent == "satisficer":
        if args.mode == "band":
            if not taus:
                raise SystemExit("--tau required for mode=band")
            # Build grid explicitly to keep types precise: (n, tau, None)
            grid = [(n, tau, None) for n in ns for tau in taus]
        elif args.mode in ("k_search", "k_greedy"):
            if not ks:
                raise SystemExit("--K required for mode=k_search/k_greedy")
            # Grid: (n, None, k)
            grid = [(n, None, k) for n in ns for k in ks]
        else:
            raise SystemExit("--mode required for satisficer")
    else:
        # Optimizer/zi: grid of (n, None, None)
        grid = [(n, None, None) for n in ns]

    runs: list[dict[str, Any]] = []
    for (n, tau, k) in grid:
        for s in range(args.seeds):
            seed = 1000 + s
            cell_dir = os.path.join(
                args.out,
                f"N{n}_{args.agent}_{args.mode or 'na'}_tau{tau}_K{k}_s{seed}",
            )
            ensure_dir(cell_dir)
            agg = run_cell(
                n=n,
                agent=args.agent,
                mode=args.mode,
                tau=tau,
                k=k,
                intervals=args.intervals,
                seed=seed,
                instrument_decisions=args.instrument_decisions,
                out_dir=cell_dir,
                price_sigma=args.price_sigma,
                buy_markup=args.buy_markup,
                sell_discount=args.sell_discount,
                optimizer_mode=(args.optimizer_mode if args.agent == "optimizer" else None),
                mechanism=args.mechanism,
                feeder_cap=args.feeder_cap,
                info_set=args.info_set,
                hetero_tau=hetero_tau,
                hetero_k=hetero_k,
            )
            runs.append(agg)

    write_manifest(args.out, vars(args), runs)
    print(f"Wrote manifest and {len(runs)} runs to {args.out}")


if __name__ == "__main__":
    main()
