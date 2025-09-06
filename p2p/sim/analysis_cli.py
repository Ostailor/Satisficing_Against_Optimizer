from __future__ import annotations

import argparse
import os

import pandas as pd

from .analysis import (
    compute_agent_wall_ms,
    load_decision_metrics,
    load_interval_metrics,
    plot_frontier,
    plot_price_volatility,
    plot_scaling,
    plot_welfare_heatmap,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Analysis CLI for P2P market runs")
    p.add_argument("--interval-csv", required=True, help="Per-interval metrics CSV path")
    p.add_argument("--decision-csv", required=False, help="Per-agent decision metrics CSV path")
    p.add_argument("--out-dir", default="outputs/analysis", help="Output directory for figures")
    p.add_argument("--scaling-csv", help="Optional CSV with columns: N, agent_type, wall_ms")
    p.add_argument("--welfare-grid-csv", help="Optional CSV with columns: tau, K, W_hat")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Load interval metrics and plot price volatility
    df_int = load_interval_metrics(args.interval_csv)
    plot_price_volatility(df_int, os.path.join(args.out_dir, "price_volatility.png"))

    # If decision metrics provided, plot a simple frontier per run
    if args.decision_csv:
        df_dec = load_decision_metrics(args.decision_csv)
        agent_stats = compute_agent_wall_ms(df_dec)
        plot_frontier(df_int, agent_stats, os.path.join(args.out_dir, "frontier.png"))

    # Optional scaling plot
    if args.scaling_csv:
        df_scal = pd.read_csv(args.scaling_csv)
        plot_scaling(df_scal, os.path.join(args.out_dir, "scaling.png"))

    # Optional welfare heatmap over (tau, K)
    if args.welfare_grid_csv:
        df_w = pd.read_csv(args.welfare_grid_csv)
        plot_welfare_heatmap(df_w, os.path.join(args.out_dir, "welfare_heatmap.png"))


if __name__ == "__main__":
    main()

