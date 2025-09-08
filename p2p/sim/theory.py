from __future__ import annotations

import argparse
import json
import os
from typing import Any

import numpy as np
import pandas as pd


def _read_json(path: str) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _mean_w_hat(interval_csv: str) -> float:
    df = pd.read_csv(interval_csv)
    return float(df["W_hat"].mean()) if not df.empty else float("nan")


def _decision_stats(dec_csv: str) -> dict[str, float]:
    """Compute acceptance rate and per-agent means from a decision CSV."""
    if not dec_csv or not os.path.exists(dec_csv):
        return {
            "accept_rate": float("nan"),
            "offers_seen_mean": float("nan"),
            "wall_ms_mean": float("nan"),
        }
    df = pd.read_csv(dec_csv)
    if df.empty:
        return {
            "accept_rate": float("nan"),
            "offers_seen_mean": float("nan"),
            "wall_ms_mean": float("nan"),
        }
    accept_rate = float((df["action_type"] == "accept").mean())
    # Per-agent means, then overall mean across agents
    g = df.groupby(["agent_id"], as_index=False).agg(
        offers_seen_mean=("offers_seen", "mean"),
        wall_ms_mean=("wall_ms", "mean"),
    )
    return {
        "accept_rate": accept_rate,
        "offers_seen_mean": float(g["offers_seen_mean"].mean()),
        "wall_ms_mean": float(g["wall_ms_mean"].mean()),
    }


def aggregate_theory(manifest_path: str) -> pd.DataFrame:
    man = _read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for r in man.get("runs", []):
        st = _decision_stats(r.get("decision_csv") or "")
        w_hat = _mean_w_hat(r["interval_csv"]) if r.get("interval_csv") else float("nan")
        rows.append(
            {
                "N": r.get("N"),
                "agent": r.get("agent"),
                "mode": r.get("mode"),
                "tau": r.get("tau"),
                "K": r.get("K"),
                "seed": r.get("seed"),
                "accept_rate": st["accept_rate"],
                "offers_seen_mean": st["offers_seen_mean"],
                "wall_ms_mean": st["wall_ms_mean"],
                "w_hat": w_hat,
            }
        )
    return pd.DataFrame(rows)


def per_cell(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["N", "agent", "mode", "tau", "K"]
    return (
        df.groupby(keys, as_index=False, dropna=False)
        .agg(
            accept_rate=("accept_rate", "mean"),
            offers_seen_mean=("offers_seen_mean", "mean"),
            wall_ms_mean=("wall_ms_mean", "mean"),
            w_hat_mean=("w_hat", "mean"),
            seeds=("seed", "nunique"),
        )
        .sort_values(keys)
    )


def diminishing_returns(df_cells: pd.DataFrame) -> pd.DataFrame:
    parts = []
    # Band over tau
    for (N,), g in df_cells[df_cells["mode"] == "band"].groupby(["N"], dropna=False):
        g2 = g.sort_values(["tau"]).reset_index(drop=True)
        for i, row in g2.iterrows():
            prev = g2.iloc[i - 1] if i > 0 else None
            parts.append(
                {
                    "mode": "band",
                    "N": N,
                    "param": "tau",
                    "value": row["tau"],
                    "w_hat_mean": row["w_hat_mean"],
                    "wall_ms_mean": row["wall_ms_mean"],
                    "accept_rate": row["accept_rate"],
                    "d_w_hat": (row["w_hat_mean"] - (prev["w_hat_mean"] if prev is not None else np.nan)),
                    "d_wall_ms": (row["wall_ms_mean"] - (prev["wall_ms_mean"] if prev is not None else np.nan)),
                    "d_accept": (row["accept_rate"] - (prev["accept_rate"] if prev is not None else np.nan)),
                }
            )
    # K-search over K
    for (N,), g in df_cells[df_cells["mode"] == "k_search"].groupby(["N"], dropna=False):
        g2 = g.sort_values(["K"]).reset_index(drop=True)
        for i, row in g2.iterrows():
            prev = g2.iloc[i - 1] if i > 0 else None
            parts.append(
                {
                    "mode": "k_search",
                    "N": N,
                    "param": "K",
                    "value": row["K"],
                    "w_hat_mean": row["w_hat_mean"],
                    "wall_ms_mean": row["wall_ms_mean"],
                    "accept_rate": row["accept_rate"],
                    "d_w_hat": (row["w_hat_mean"] - (prev["w_hat_mean"] if prev is not None else np.nan)),
                    "d_wall_ms": (row["wall_ms_mean"] - (prev["wall_ms_mean"] if prev is not None else np.nan)),
                    "d_accept": (row["accept_rate"] - (prev["accept_rate"] if prev is not None else np.nan)),
                }
            )
    # K-greedy over K
    for (N,), g in df_cells[df_cells["mode"] == "k_greedy"].groupby(["N"], dropna=False):
        g2 = g.sort_values(["K"]).reset_index(drop=True)
        for i, row in g2.iterrows():
            prev = g2.iloc[i - 1] if i > 0 else None
            parts.append(
                {
                    "mode": "k_greedy",
                    "N": N,
                    "param": "K",
                    "value": row["K"],
                    "w_hat_mean": row["w_hat_mean"],
                    "wall_ms_mean": row["wall_ms_mean"],
                    "accept_rate": row["accept_rate"],
                    "d_w_hat": (row["w_hat_mean"] - (prev["w_hat_mean"] if prev is not None else np.nan)),
                    "d_wall_ms": (row["wall_ms_mean"] - (prev["wall_ms_mean"] if prev is not None else np.nan)),
                    "d_accept": (row["accept_rate"] - (prev["accept_rate"] if prev is not None else np.nan)),
                }
            )
    return pd.DataFrame(parts)


def offers_vs_time_regression(df_cells: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (agent, mode), g in df_cells.groupby(["agent", "mode"], dropna=False):
        x = g["offers_seen_mean"].to_numpy(dtype=float)
        y = g["wall_ms_mean"].to_numpy(dtype=float)
        mask = ~np.isnan(x) & ~np.isnan(y)
        x = x[mask]
        y = y[mask]
        if x.size >= 2:
            coeffs = np.polyfit(x, y, 1)
            y_pred = np.polyval(coeffs, x)
            ss_res = float(np.sum((y - y_pred) ** 2))
            ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else float("nan")
            slope = float(coeffs[0])
        else:
            slope, r2 = float("nan"), float("nan")
        rows.append({"agent": agent, "mode": mode, "slope_ms_per_offer": slope, "R2": r2, "points": int(x.size)})
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Phase 9 theory checks: acceptance vs tau/K; offers vs time; diminishing returns")
    p.add_argument("--manifests", required=True, help="Comma-separated manifest.json paths")
    p.add_argument("--out-dir", default="outputs/analysis/phase9", help="Output directory")
    args = p.parse_args()

    man_paths = [s for s in (m.strip() for m in args.manifests.split(",")) if s]
    os.makedirs(args.out_dir, exist_ok=True)

    # Load and concatenate per-run theory stats
    frames = [aggregate_theory(m) for m in man_paths]
    df_runs = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df_runs.to_csv(os.path.join(args.out_dir, "runs_flat.csv"), index=False)

    # Aggregate per cell (N, agent, mode, tau, K)
    df_cells = per_cell(df_runs)
    df_cells.to_csv(os.path.join(args.out_dir, "cells_summary.csv"), index=False)

    # Diminishing returns over tau and K
    dr = diminishing_returns(df_cells)
    dr.to_csv(os.path.join(args.out_dir, "diminishing_returns.csv"), index=False)

    # Regression: wall_ms ~ offers_seen
    reg = offers_vs_time_regression(df_cells)
    reg.to_csv(os.path.join(args.out_dir, "offers_vs_time_regression.csv"), index=False)

    print(f"Wrote Phase 9 outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
