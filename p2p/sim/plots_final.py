from __future__ import annotations

import argparse
import logging
import os

import matplotlib.pyplot as plt
import pandas as pd


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def plot_frontier_overlay_cda(overlay_csv: str, out_png: str) -> None:
    df = pd.read_csv(overlay_csv)
    # Expect columns: N, agent, mode, w_hat_mean, wall_ms_mean, label
    plt.figure(figsize=(6.5, 4.5))
    markers = {"band": "o", "k_search": "^", "k_greedy": "s", "optimizer": "x"}
    # Map labels to (agent,mode)
    # If 'label' exists use it, else infer from agent/mode
    groups = df.groupby(["agent", "mode", "N"], as_index=False).agg(
        w_hat_mean=("w_hat_mean", "mean"), wall_ms_mean=("wall_ms_mean", "mean")
    )
    for (agent, mode), g in groups.groupby(["agent", "mode"], as_index=False):
        m = (
            markers.get(mode or "", "o") if agent != "optimizer" else markers["optimizer"]
        )
        label_str = f"{agent}:{mode or 'na'}"
        plt.plot(
            g["wall_ms_mean"],
            g["w_hat_mean"],
            marker=m,
            linestyle="-",
            label=label_str,
        )
    plt.xlabel("Per-agent wall time (ms)")
    plt.ylabel("Normalized welfare (Ŵ)")
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_scaling(opt_scaling_csv: str, kg_scaling_csv: str, out_png: str) -> None:
    dfo = pd.read_csv(opt_scaling_csv)
    dfk = pd.read_csv(kg_scaling_csv)
    plt.figure(figsize=(6.5, 4.0))
    for df, name, mk in [(dfo, "optimizer", "x"), (dfk, "k_greedy", "s")]:
        g = df.groupby("N", as_index=False).agg(wall_ms_mean=("wall_ms_mean", "mean"))
        g = g.sort_values("N")
        plt.plot(g["N"], g["wall_ms_mean"], marker=mk, label=name)
    plt.xlabel("N agents")
    plt.ylabel("Per-agent wall time (ms)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_heatmap_band(band_frontier_csv: str, out_png: str) -> None:
    df = pd.read_csv(band_frontier_csv)
    # Use aggregated cells per (N,tau)
    sub = df[(df["agent"] == "satisficer") & (df["mode"] == "band")]
    piv = sub.pivot_table(index="tau", columns="N", values="w_hat_mean", aggfunc="mean")
    plt.figure(figsize=(6.0, 4.0))
    im = plt.imshow(piv.values, aspect="auto", origin="lower", cmap="viridis")
    plt.colorbar(im, label="Ŵ")
    plt.xticks(range(len(piv.columns)), piv.columns)
    plt.yticks(range(len(piv.index)), piv.index)
    plt.xlabel("N agents")
    plt.ylabel("τ (%)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_robustness_call(kg_overlay_csv: str, out_png: str) -> None:
    df = pd.read_csv(kg_overlay_csv)
    # Keep k_greedy rows only
    df = df[(df["agent"] == "satisficer") & (df["mode"] == "k_greedy")]
    plt.figure(figsize=(6.5, 4.5))
    for label, g in df.groupby("label"):
        g2 = g.groupby("N", as_index=False).agg(
            w_hat_mean=("w_hat_mean", "mean"),
            wall_ms_mean=("wall_ms_mean", "mean"),
        )
        g2 = g2.sort_values("N")
        plt.plot(g2["wall_ms_mean"], g2["w_hat_mean"], marker="o", linestyle="-", label=label)
    plt.xlabel("Per-agent wall time (ms)")
    plt.ylabel("Normalized welfare (Ŵ)")
    plt.legend(title="auction", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(
        description="Generate final publication figures from aggregated CSVs"
    )
    p.add_argument(
        "--out-dir",
        default="outputs/analysis/figs_final",
        help="Directory for output figures",
    )
    # Default paths based on the final pipeline
    p.add_argument(
        "--overlay-cda",
        default="outputs/analysis/overlay_v4/combined_frontier_pareto_by_N.csv",
    )
    p.add_argument(
        "--overlay-kg-call",
        default=(
            "outputs/analysis/overlay_kg_robust_v4/combined_frontier_pareto_by_N.csv"
        ),
    )
    p.add_argument("--opt-scaling", default="outputs/analysis/exp_opt_v4/scaling.csv")
    p.add_argument("--kg-scaling", default="outputs/analysis/exp_kg_v4/scaling.csv")
    p.add_argument("--band-frontier", default="outputs/analysis/exp_band_v4/frontier.csv")
    p.add_argument(
        "--overlay-kg-ticker",
        default=(
            "outputs/analysis/overlay_kg_ticker_v4/combined_frontier_pareto_by_N.csv"
        ),
    )
    args = p.parse_args()

    _ensure_dir(args.out_dir)
    plot_frontier_overlay_cda(
        args.overlay_cda, os.path.join(args.out_dir, "frontier_overlay_cda.png")
    )
    plot_scaling(
        args.opt_scaling, args.kg_scaling, os.path.join(args.out_dir, "scaling_opt_vs_kgreedy.png")
    )
    plot_heatmap_band(
        args.band_frontier, os.path.join(args.out_dir, "heatmap_band.png")
    )
    plot_robustness_call(
        args.overlay_kg_call, os.path.join(args.out_dir, "robustness_call.png")
    )
    # Ticker overlay (book vs ticker for k_greedy)
    try:
        df = pd.read_csv(args.overlay_kg_ticker)
        plt.figure(figsize=(6.5, 4.5))
        for label, g in df.groupby("label"):
            g2 = g.groupby("N", as_index=False).agg(
                w_hat_mean=("w_hat_mean", "mean"),
                wall_ms_mean=("wall_ms_mean", "mean"),
            )
            g2 = g2.sort_values("N")
            plt.plot(g2["wall_ms_mean"], g2["w_hat_mean"], marker="o", linestyle="-", label=label)
        plt.xlabel("Per-agent wall time (ms)")
        plt.ylabel("Normalized welfare (Ŵ)")
        plt.legend(title="info", fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(args.out_dir, "overlay_kg_ticker.png"), dpi=200)
        plt.close()
    except Exception as exc:  # noqa: BLE001
        logging.warning("Could not generate overlay_kg_ticker: %s", exc)
    logging.info("Wrote figures to %s", args.out_dir)


if __name__ == "__main__":
    main()
