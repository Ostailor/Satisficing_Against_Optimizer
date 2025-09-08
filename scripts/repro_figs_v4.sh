#!/usr/bin/env bash
set -euo pipefail

# Reproduce main figures from existing experiment outputs (no LaTeX build).
#
# Usage:
#   bash scripts/repro_figs_v4.sh            # overlays + figures
#   bash scripts/repro_figs_v4.sh --full     # run full pipeline (slow!) then figures
#
# Notes:
# - Expects manifests under outputs/exp_*_v4 from prior runs.
# - Overlays will also emit combined_runs.csv used by ratio plots.
# - Paper build is intentionally not supported here (CI/GitHub may lack LaTeX).

FULL=0
for arg in "$@"; do
  case "$arg" in
    --full)  FULL=1  ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [[ $FULL -eq 1 ]]; then
  echo "[repro] Running full pipeline (experiments + overlays + figures + paper)"
  bash scripts/run_final_v4.sh
  exit 0
fi

echo "[repro] Regenerating overlays (writes combined_runs.csv as well)"
python -m p2p.sim.overlay \
  --manifests outputs/exp_band_v4/manifest.json,outputs/exp_k_v4/manifest.json,outputs/exp_kg_v4/manifest.json,outputs/exp_opt_v4/manifest.json \
  --labels band,k_search,k_greedy,opt_greedy \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_v4

python -m p2p.sim.overlay \
  --manifests outputs/exp_kg_v4/manifest.json,outputs/exp_kg_call_v4/manifest.json,outputs/exp_kg_call_cap_v4/manifest.json \
  --labels cda,call,call_cap \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_kg_robust_v4

python -m p2p.sim.overlay \
  --manifests outputs/exp_kg_v4/manifest.json,outputs/exp_kg_ticker_v4/manifest.json \
  --labels book,ticker \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_kg_ticker_v4

# Optional: optimizer robustness overlay (not used by core figures but handy)
python -m p2p.sim.overlay \
  --manifests outputs/exp_opt_v4/manifest.json,outputs/exp_opt_call_v4/manifest.json \
  --labels opt_cda,opt_call \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_opt_robust_v4 || true

echo "[repro] Regenerating final figures"
FIG_DIR=outputs/analysis/figs_final
mkdir -p "$FIG_DIR"
python -m p2p.sim.plots_final --out-dir "$FIG_DIR"

echo "[repro] Done. Figures in $FIG_DIR"
