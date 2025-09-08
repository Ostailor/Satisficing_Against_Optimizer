from __future__ import annotations

import argparse
import json
import os
from typing import Any

import pandas as pd

from .analysis import bootstrap_ci


def _read_json(path: str) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _mean_wall_ms(dec_csv: str) -> tuple[float, float, float]:
    """Return (wall_ms_mean, offers_seen_mean, solver_calls_mean) from a decision CSV.

    Computes mean per-agent wall_ms across intervals, then averages across agents.
    """
    if not dec_csv or not os.path.exists(dec_csv):
        return float("nan"), float("nan"), float("nan")
    df = pd.read_csv(dec_csv)
    if df.empty:
        return float("nan"), float("nan"), float("nan")
    g = df.groupby(["agent_id", "agent_type"], as_index=False).agg(
        wall_ms=("wall_ms", "mean"),
        offers_seen=("offers_seen", "mean"),
        solver_calls=("solver_calls", "mean"),
    )
    return (
        float(g["wall_ms"].mean()),
        float(g["offers_seen"].mean()),
        float(g["solver_calls"].mean()),
    )


def _mean_w_hat(interval_csv: str) -> float:
    df = pd.read_csv(interval_csv)
    if df.empty:
        return float("nan")
    return float(df["W_hat"].mean())


def _mean_W(interval_csv: str) -> float:
    """Return mean quote-surplus welfare W across intervals for a run.

    Using a mean (rather than sum) keeps runs comparable across different
    interval lengths; ratios like R_W are invariant to the scale anyway.
    """
    df = pd.read_csv(interval_csv)
    if df.empty:
        return float("nan")
    return float(df["W"].mean())


def compute_runs_from_manifest(manifest_path: str) -> pd.DataFrame:
    """Return per-run metrics (no seed aggregation) from a manifest.

    Columns: N, agent, mode, tau, K, seed, w_hat, W, wall_ms, offers_seen, solver_calls.
    """
    man = _read_json(manifest_path)
    runs = man.get("runs", [])
    rows: list[dict[str, Any]] = []
    for r in runs:
        w_hat = _mean_w_hat(r["interval_csv"])
        W_mean = _mean_W(r["interval_csv"])
        wall_ms, offers_seen, solver_calls = _mean_wall_ms(r.get("decision_csv") or "")
        rows.append(
            {
                "N": r["N"],
                "agent": r["agent"],
                "mode": r.get("mode"),
                "tau": r.get("tau"),
                "K": r.get("K"),
                "seed": r.get("seed"),
                "w_hat": w_hat,
                "W": W_mean,
                "wall_ms": wall_ms,
                "offers_seen": offers_seen,
                "solver_calls": solver_calls,
            }
        )
    return pd.DataFrame(rows)


def compute_frontier_from_manifest(manifest_path: str) -> pd.DataFrame:
    man = _read_json(manifest_path)
    runs = man.get("runs", [])
    rows = []
    for r in runs:
        w_hat = _mean_w_hat(r["interval_csv"])
        wall_ms, offers_seen, solver_calls = _mean_wall_ms(r.get("decision_csv") or "")
        rows.append(
            {
                "N": r["N"],
                "agent": r["agent"],
                "mode": r.get("mode"),
                "tau": r.get("tau"),
                "K": r.get("K"),
                "seed": r.get("seed"),
                "w_hat": w_hat,
                "wall_ms": wall_ms,
                "offers_seen": offers_seen,
                "solver_calls": solver_calls,
            }
        )
    df = pd.DataFrame(rows)
    # Aggregate across seeds for each cell. Keep NaN groups (e.g., K=None in band mode).
    keys = ["N", "agent", "mode", "tau", "K"]
    agg = df.groupby(keys, as_index=False, dropna=False, sort=True).agg(
        w_hat_mean=("w_hat", "mean"),
        wall_ms_mean=("wall_ms", "mean"),
        offers_seen_mean=("offers_seen", "mean"),
        solver_calls_mean=("solver_calls", "mean"),
        seeds=("seed", "nunique"),
    )
    # Bootstrap CI for w_hat per cell in the same sorted order
    ci_lo = []
    ci_hi = []
    for _, group in df.groupby(keys, dropna=False, sort=True):
        lo, hi = bootstrap_ci(group["w_hat"].dropna().tolist(), n_boot=1000)
        ci_lo.append(lo)
        ci_hi.append(hi)
    agg["w_hat_lo"] = ci_lo
    agg["w_hat_hi"] = ci_hi
    return agg


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    """Return non-dominated points (maximize w_hat_mean, minimize wall_ms_mean)."""
    pts = df[["w_hat_mean", "wall_ms_mean"]].values.tolist()
    keep = [True] * len(pts)
    for i, (w_i, c_i) in enumerate(pts):
        if not keep[i]:
            continue
        for j, (w_j, c_j) in enumerate(pts):
            if i == j:
                continue
            if (w_j >= w_i and c_j <= c_i) and (w_j > w_i or c_j < c_i):
                keep[i] = False
                break
    return df[keep].copy()


def grouped_pareto(frontier_df: pd.DataFrame, group_keys: list[str]) -> pd.DataFrame:
    """Compute Pareto frontiers within groups defined by `group_keys`.

    Returns the concatenated set of non-dominated rows per group.
    """
    if not group_keys:
        return pareto_frontier(frontier_df)
    parts = []
    for _, sub in frontier_df.groupby(group_keys, dropna=False, sort=True):
        parts.append(pareto_frontier(sub))
    if not parts:
        return frontier_df.head(0)
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Aggregate runs into frontier/scaling CSVs")
    p.add_argument("--manifest", required=True, help="Path to manifest.json")
    p.add_argument("--out-dir", default="outputs/analysis", help="Directory to write CSVs")
    p.add_argument(
        "--pareto-groupby",
        default="",
        help=(
            "Comma-separated keys to group by before Pareto (e.g., 'N' or 'agent,N'). "
            "Empty for global."
        ),
    )
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    frontier = compute_frontier_from_manifest(args.manifest)
    frontier.to_csv(os.path.join(args.out_dir, "frontier.csv"), index=False)
    # Global Pareto frontier across all cells
    pareto = pareto_frontier(frontier)
    pareto.to_csv(os.path.join(args.out_dir, "frontier_pareto.csv"), index=False)
    # Optional grouped Pareto frontier
    group_keys = [k for k in (args.pareto_groupby.split(",") if args.pareto_groupby else []) if k]
    if group_keys:
        gp = grouped_pareto(frontier, group_keys)
        # Name file to reflect grouping keys
        suffix = "_by_" + "_".join(group_keys)
        gp.to_csv(os.path.join(args.out_dir, f"frontier_pareto{suffix}.csv"), index=False)
    # Scaling: average wall_ms by agent and N
    scaling = frontier.groupby(["agent", "N"], as_index=False).agg(
        wall_ms_mean=("wall_ms_mean", "mean")
    )
    scaling.to_csv(os.path.join(args.out_dir, "scaling.csv"), index=False)
    print(f"Wrote frontier, frontier_pareto, scaling to {args.out_dir}")


if __name__ == "__main__":
    main()
