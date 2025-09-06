from __future__ import annotations

from collections.abc import Iterable

import matplotlib.pyplot as plt
import pandas as pd


def bootstrap_ci(
    values: Iterable[float],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Nonparametric bootstrap percentile CI for the mean of `values`.

    Returns (lo, hi) bounds.
    """
    rng = pd.util.random.RandomState(seed)
    arr = pd.Series(list(values), dtype=float)
    if len(arr) == 0:
        return (float("nan"), float("nan"))
    boots = []
    for _ in range(n_boot):
        sample = arr.sample(n=len(arr), replace=True, random_state=rng)
        boots.append(sample.mean())
    lo = pd.Series(boots).quantile(alpha / 2)
    hi = pd.Series(boots).quantile(1 - alpha / 2)
    return float(lo), float(hi)


def load_interval_metrics(path: str) -> pd.DataFrame:
    """Load per-interval metrics CSV produced by the runner.

    Expected columns:
    t, trades, traded_kwh, posted_buy_kwh, posted_sell_kwh,
    price_mean, price_var, W, W_bound, W_hat.
    """
    df = pd.read_csv(path)
    return df


def plot_frontier(df: pd.DataFrame, agent_stats: pd.DataFrame, out_png: str) -> None:
    """Plot welfare vs per-agent compute frontier.

    `agent_stats` should have columns: agent_id, agent_type, wall_ms (mean per step).
    `df` should include W_hat.
    This function produces a scatter; dominance filtering can be added upstream as needed.
    """
    plt.figure(figsize=(6, 4))
    # Aggregate per run (mean W_hat) and per-agent compute
    w_hat = df["W_hat"].mean()
    comp = agent_stats.groupby("agent_type")["wall_ms"].mean()
    for atype, ms in comp.items():
        plt.scatter(ms, w_hat, label=atype)
    plt.xlabel("Per-agent wall time (ms)")
    plt.ylabel("Normalized welfare Ŵ")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)


def plot_scaling(agent_stats_by_n: pd.DataFrame, out_png: str) -> None:
    """Plot per-agent wall time vs N (scaling). Expects columns: N, agent_type, wall_ms."""
    plt.figure(figsize=(6, 4))
    for atype, g in agent_stats_by_n.groupby("agent_type"):
        g = g.sort_values("N")
        plt.plot(g["N"], g["wall_ms"], marker="o", label=atype)
    plt.xlabel("N agents")
    plt.ylabel("Per-agent wall time (ms)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)


def plot_welfare_heatmap(df: pd.DataFrame, out_png: str) -> None:
    """Plot a heatmap of W_hat by (tau, K). Expects columns: tau, K, W_hat."""
    pivot = df.pivot_table(index="tau", columns="K", values="W_hat", aggfunc="mean")
    plt.figure(figsize=(6, 4))
    im = plt.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis")
    plt.colorbar(im, label="Ŵ")
    plt.xticks(range(len(pivot.columns)), pivot.columns)
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel("K")
    plt.ylabel("tau (%)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)


def plot_price_volatility(df: pd.DataFrame, out_png: str) -> None:
    """Plot price variance vs t from interval-metrics DataFrame."""
    plt.figure(figsize=(6, 3.5))
    plt.plot(df["t"], df["price_var"], marker=".")
    plt.xlabel("Interval t")
    plt.ylabel("Price variance")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)


def load_decision_metrics(path: str) -> pd.DataFrame:
    """Load per-agent decision metrics CSV (Phase 4)."""
    return pd.read_csv(path)


def compute_agent_wall_ms(decisions: pd.DataFrame) -> pd.DataFrame:
    """Compute mean per-agent wall time (ms) by agent_type."""
    g = decisions.groupby("agent_type", as_index=False)["wall_ms"].mean()
    g.rename(columns={"wall_ms": "wall_ms"}, inplace=True)
    return g
