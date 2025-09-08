from __future__ import annotations

import argparse
import logging
import os

import matplotlib.pyplot as plt
import pandas as pd

from .analysis import bootstrap_ci


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


def _join_ratio_to_opt(runs_csv: str) -> pd.DataFrame:
    """Compute per-run ratio R_W = W_sat / W_opt by joining on (N, seed).

    Returns a DataFrame with satisficer rows augmented with R_W and optimizer W, filtered
    to rows where a matching optimizer run exists.
    """
    df = pd.read_csv(runs_csv)
    sat = df[df["agent"] == "satisficer"].copy()
    opt = df[df["agent"] == "optimizer"][["N", "seed", "W", "w_hat", "wall_ms", "label"]].copy()
    opt = opt.rename(
        columns={
            "W": "W_opt",
            "w_hat": "w_hat_opt",
            "wall_ms": "wall_ms_opt",
            "label": "label_opt",
        }
    )
    merged = sat.merge(opt, on=["N", "seed"], how="inner")
    merged["R_W"] = merged["W"] / merged["W_opt"]
    return merged


def plot_ratio_to_optimizer(runs_csv: str, out_png: str) -> None:
    df = _join_ratio_to_opt(runs_csv)
    # Aggregate per cell (N, mode, tau, K) with bootstrap CI over seeds
    plt.figure(figsize=(6.8, 4.6))
    mode_markers = {"band": "o", "k_search": "^", "k_greedy": "s"}
    cell = (
        df.groupby(["N", "mode", "tau", "K"], as_index=False, dropna=False)
        .agg(
            wall_ms_mean=("wall_ms", "mean"),
            R_W_mean=("R_W", "mean"),
        )
        .copy()
    )
    # Compute CIs separately to preserve grouping order
    ci_lo = []
    ci_hi = []
    for _, g in df.groupby(["N", "mode", "tau", "K"], as_index=False, dropna=False):
        lo, hi = bootstrap_ci(g["R_W"].tolist(), n_boot=2000)
        ci_lo.append(lo)
        ci_hi.append(hi)
    cell["R_W_lo"] = ci_lo
    cell["R_W_hi"] = ci_hi
    for (mode, n_val), g in cell.groupby(["mode", "N"], as_index=False):
        marker = mode_markers.get(mode or "", "o")
        # Build concise label with parameter
        if mode == "band":
            param = [f"tau={int(x)}" if pd.notna(x) else "tau=na" for x in g["tau"]]
        else:
            param = [f"K={int(x)}" if pd.notna(x) else "K=na" for x in g["K"]]
        labels = [f"{mode}:{p}:N={n_val}" for p in param]
        # Plot each row to attach distinct labels cleanly
        for i in range(len(g)):
            yerr_low = g.iloc[i]["R_W_mean"] - g.iloc[i]["R_W_lo"]
            yerr_high = g.iloc[i]["R_W_hi"] - g.iloc[i]["R_W_mean"]
            plt.errorbar(
                [g.iloc[i]["wall_ms_mean"]],
                [g.iloc[i]["R_W_mean"]],
                yerr=[[yerr_low], [yerr_high]],
                fmt=marker,
                capsize=3,
                linestyle="none",
                elinewidth=0.8,
                label=labels[i],
            )
        # Avoid duplicate legend entries across N groups handled by Matplotlib dedupe
    # Shade H1 target band 0.90–0.98
    plt.axhspan(0.90, 0.98, color="gray", alpha=0.10, zorder=0)
    plt.xlabel("Per-agent wall time (ms)")
    plt.ylabel("R_W = W_sat / W_opt")
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_connector_overlay(overlay_csv: str, runs_csv: str, out_png: str) -> None:
    """On Ŵ vs ms axes, connect optimizer to satisficer per-cell and annotate R_W.

    Uses aggregated Ŵ and wall_ms from overlay_csv; computes R_W from per-run W means.
    """
    df_front = pd.read_csv(overlay_csv)
    df_runs = _join_ratio_to_opt(runs_csv)
    # Aggregate W means per cell for annotation
    w_agg = (
        df_runs.groupby(["N", "agent", "mode", "tau", "K"], as_index=False, dropna=False)
        .agg(W_mean=("W", "mean"))
        .copy()
    )
    w_opt_agg = (
        df_runs.groupby(["N"], as_index=False)
        .agg(W_opt_mean=("W_opt", "mean"))
        .copy()
    )
    plt.figure(figsize=(6.8, 4.8))
    # Plot optimizer aggregated points
    opt_front = df_front[df_front["agent"] == "optimizer"].copy()
    plt.scatter(
        opt_front["wall_ms_mean"], opt_front["w_hat_mean"], marker="x", c="k", label="optimizer"
    )
    # For each satisficer cell, plot point and connector to same-N optimizer
    sat_front = df_front[df_front["agent"] == "satisficer"].copy()
    for _, row in sat_front.iterrows():
        n_val = row["N"]
        mode = row["mode"]
        tau = row.get("tau")
        k_val = row.get("K")
        # Point
        plt.scatter(row["wall_ms_mean"], row["w_hat_mean"], s=30, alpha=0.9)
        # Connector
        opt_match = opt_front[opt_front["N"] == n_val]
        if not opt_match.empty:
            x0 = float(opt_match.iloc[0]["wall_ms_mean"])  # optimizer
            y0 = float(opt_match.iloc[0]["w_hat_mean"])
            x1 = float(row["wall_ms_mean"])  # satisficer
            y1 = float(row["w_hat_mean"])
            plt.plot([x0, x1], [y0, y1], color="gray", linewidth=0.8, alpha=0.6)
            # Annotate ratio R_W using aggregated W means
            cond = (
                (w_agg["N"] == n_val)
                & (w_agg["mode"] == mode)
                & (w_agg["tau"] == tau)
                & (w_agg["K"] == k_val)
            )
            w_sat = w_agg[cond]
            w_opt = w_opt_agg[w_opt_agg["N"] == n_val]
            if not w_sat.empty and not w_opt.empty:
                w_opt_mean = float(w_opt.iloc[0]["W_opt_mean"])
                rw = float("nan")
                if w_opt_mean > 0:
                    rw = float(w_sat.iloc[0]["W_mean"]) / w_opt_mean
                plt.text(
                    (x0 + x1) / 2,
                    (y0 + y1) / 2,
                    f"{rw:.2f}×",
                    fontsize=7,
                    color="gray",
                )
    plt.xlabel("Per-agent wall time (ms)")
    plt.ylabel("Normalized welfare (Ŵ)")
    plt.title("Optimizer→Satisficer connectors with R_W annotations")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_small_multiples(overlay_csv: str, runs_csv: str, out_png: str) -> None:
    """Two panels: left Ŵ vs ms; right R_W vs ms (with 0.90–0.98 band)."""
    df_front = pd.read_csv(overlay_csv)
    df_ratio = _join_ratio_to_opt(runs_csv)
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.5))
    # Left: Ŵ vs ms
    markers = {"band": "o", "k_search": "^", "k_greedy": "s", "optimizer": "x"}
    groups = df_front.groupby(["agent", "mode", "N"], as_index=False).agg(
        w_hat_mean=("w_hat_mean", "mean"), wall_ms_mean=("wall_ms_mean", "mean")
    )
    ax = axs[0]
    for (agent, mode), g in groups.groupby(["agent", "mode"], as_index=False):
        m = markers.get(mode or "", "o") if agent != "optimizer" else markers["optimizer"]
        label_str = f"{agent}:{mode or 'na'}"
        ax.plot(g["wall_ms_mean"], g["w_hat_mean"], marker=m, linestyle="-", label=label_str)
    ax.set_xlabel("Per-agent wall time (ms)")
    ax.set_ylabel("Normalized welfare (Ŵ)")
    ax.legend(ncol=1, fontsize=8)
    # Right: R_W vs ms
    ax2 = axs[1]
    mode_markers = {"band": "o", "k_search": "^", "k_greedy": "s"}
    for (mode, n_val), g in df_ratio.groupby(["mode", "N"], as_index=False):
        marker = mode_markers.get(mode or "", "o")
        ax2.scatter(
            g["wall_ms"], g["R_W"], marker=marker, alpha=0.7, label=f"{mode or 'na'}:N={n_val}"
        )
    ax2.axhspan(0.90, 0.98, color="gray", alpha=0.10, zorder=0)
    ax2.set_xlabel("Per-agent wall time (ms)")
    ax2.set_ylabel("R_W = W_sat / W_opt")
    ax2.legend(ncol=1, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


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
    p.add_argument(
        "--overlay-runs",
        default="outputs/analysis/overlay_v4/combined_runs.csv",
        help="Combined per-run metrics (for ratio plots)",
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

    # Ratio-to-optimizer and connector/small-multiple plots
    try:
        plot_ratio_to_optimizer(
            args.overlay_runs, os.path.join(args.out_dir, "ratio_to_optimizer.png")
        )
        plot_connector_overlay(
            args.overlay_cda, args.overlay_runs, os.path.join(args.out_dir, "connector_overlay.png")
        )
        out_path = os.path.join(args.out_dir, "frontier_and_ratio.png")
        plot_small_multiples(args.overlay_cda, args.overlay_runs, out_path)
    except Exception as exc:  # noqa: BLE001
        logging.warning("Could not generate ratio/connector/small-multiple plots: %s", exc)
    logging.info("Wrote figures to %s", args.out_dir)


if __name__ == "__main__":
    main()
