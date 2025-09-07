from __future__ import annotations

import argparse
import os

import pandas as pd

from .aggregate import compute_frontier_from_manifest, grouped_pareto


def _split_csv_arg(arg: str | None) -> list[str]:
    if not arg:
        return []
    return [s for s in (x.strip() for x in arg.split(",")) if s]


def combine_frontiers(manifests: list[str], labels: list[str] | None = None) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    labels = labels or []
    if labels and len(labels) != len(manifests):
        raise SystemExit("--labels must match number of --manifests (or omit labels)")
    for i, m in enumerate(manifests):
        df = compute_frontier_from_manifest(m)
        df["label"] = labels[i] if labels else os.path.basename(os.path.dirname(m)) or f"m{i}"
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Overlay multiple manifests into combined frontier CSVs"
        )
    )
    p.add_argument(
        "--manifests",
        required=True,
        help="Comma-separated list of manifest.json paths",
    )
    p.add_argument(
        "--labels",
        default="",
        help="Optional comma-separated labels matching manifests",
    )
    p.add_argument(
        "--pareto-groupby",
        default="N",
        help="Group keys for Pareto before dominance (e.g., 'N' or 'agent,N')",
    )
    p.add_argument(
        "--out-dir",
        default="outputs/analysis/overlay",
        help="Directory to write combined CSVs",
    )
    args = p.parse_args()

    man_paths = _split_csv_arg(args.manifests)
    labels = _split_csv_arg(args.labels)
    os.makedirs(args.out_dir, exist_ok=True)

    frontier = combine_frontiers(manifests=man_paths, labels=labels)
    if frontier.empty:
        print("No data loaded; check --manifests")
        return
    frontier.to_csv(os.path.join(args.out_dir, "combined_frontier.csv"), index=False)

    group_keys = [k for k in _split_csv_arg(args.pareto_groupby) if k]
    pareto = grouped_pareto(frontier, group_keys)
    suffix = "_by_" + "_".join(group_keys) if group_keys else ""
    pareto.to_csv(
        os.path.join(args.out_dir, f"combined_frontier_pareto{suffix}.csv"), index=False
    )
    # Also provide a per-label summary for convenience
    summ = (
        frontier.groupby(["label", "agent", "mode", "N"], as_index=False)
        .agg(
            w_hat_mean=("w_hat_mean", "mean"),
            wall_ms_mean=("wall_ms_mean", "mean"),
            seeds=("seeds", "sum"),
        )
        .sort_values(["N", "label", "agent", "mode"])
    )
    summ.to_csv(os.path.join(args.out_dir, "combined_summary.csv"), index=False)
    print(f"Wrote combined CSVs to {args.out_dir}")


if __name__ == "__main__":
    main()
