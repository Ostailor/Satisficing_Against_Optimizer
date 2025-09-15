#!/usr/bin/env bash
set -euo pipefail

# Final end-to-end run script (v4)
# - Runs core CDA experiments (optimizer, band, k_search, k_greedy)
# - Runs robustness pilots (ticker-only, call auction, call+feeder cap)
# - Aggregates frontiers and scaling
# - Builds overlays
# - Runs theory checks
# - Generates a few representative figures
#
# Pricing realism:
# - We DO NOT set fixed --buy-markup/--sell-discount; Prosumer samples per-agent premia by default.
# - We DO set --price-sigma 1.0 for intraday quote dispersion.

NS_CDA="50,100,200,500"
NS_ROB="100,200,500"
SEEDS=5
INTERVALS=288
SIGMA=1.0

# Timestamp and archive any existing outputs directory for a fresh run
TS=$(date +%Y%m%d-%H%M%S)
if [[ -d outputs ]]; then
  ARCHIVE_DIR="outputs_${TS}"
  echo "Archiving existing ./outputs -> ${ARCHIVE_DIR}"
  mv outputs "${ARCHIVE_DIR}"
fi
mkdir -p outputs

echo "[1/7] Core CDA experiments (this can take hours)"
python -m p2p.sim.exp_runner --agent optimizer  --optimizer-mode greedy --N ${NS_CDA} --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism cda  --info-set book --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_opt_v4
python -m p2p.sim.exp_runner --agent satisficer --mode band      --N ${NS_CDA} --tau 1,5,10,20    --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism cda  --info-set book --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_band_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_search  --N ${NS_CDA} --K 1,3,5         --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism cda  --info-set book --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_k_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy  --N ${NS_CDA} --K 1,3,5         --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism cda  --info-set book --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_kg_v4

echo "[2/7] Robustness: ticker-only info (CDA)"
python -m p2p.sim.exp_runner --agent optimizer  --optimizer-mode greedy --N ${NS_ROB} --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism cda  --info-set ticker --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_opt_ticker_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy          --N ${NS_ROB} --K 1,3,5  --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism cda  --info-set ticker --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_kg_ticker_v4

echo "[3/7] Robustness: call auction (no cap and cap=500 kW)"
python -m p2p.sim.exp_runner --agent optimizer  --optimizer-mode greedy --N ${NS_ROB} --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism call --info-set book   --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_opt_call_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy          --N ${NS_ROB} --K 1,3,5  --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism call --info-set book   --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_kg_call_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy          --N ${NS_ROB} --K 1,3,5  --seeds ${SEEDS} --intervals ${INTERVALS} --mechanism call --info-set book --feeder-cap 500 --price-sigma ${SIGMA} --instrument-decisions --out outputs/exp_kg_call_cap_v4

echo "[4/7] Aggregation (frontier, Pareto-by-N, scaling)"
python -m p2p.sim.aggregate --manifest outputs/exp_opt_v4/manifest.json         --out-dir outputs/analysis/exp_opt_v4         --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_band_v4/manifest.json        --out-dir outputs/analysis/exp_band_v4        --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_k_v4/manifest.json           --out-dir outputs/analysis/exp_k_v4           --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_kg_v4/manifest.json          --out-dir outputs/analysis/exp_kg_v4          --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_opt_ticker_v4/manifest.json  --out-dir outputs/analysis/exp_opt_ticker_v4  --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_kg_ticker_v4/manifest.json   --out-dir outputs/analysis/exp_kg_ticker_v4   --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_opt_call_v4/manifest.json    --out-dir outputs/analysis/exp_opt_call_v4    --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_kg_call_v4/manifest.json     --out-dir outputs/analysis/exp_kg_call_v4     --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_kg_call_cap_v4/manifest.json --out-dir outputs/analysis/exp_kg_call_cap_v4 --pareto-groupby N

echo "[5/7] Overlays (frontiers across experiments)"
# Core overlay: band, k_search, k_greedy, optimizer (CDA)
python -m p2p.sim.overlay \
  --manifests outputs/exp_band_v4/manifest.json,outputs/exp_k_v4/manifest.json,outputs/exp_kg_v4/manifest.json,outputs/exp_opt_v4/manifest.json \
  --labels band,k_search,k_greedy,opt_greedy \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_v4

# Robustness overlays
python -m p2p.sim.overlay \
  --manifests outputs/exp_kg_v4/manifest.json,outputs/exp_kg_call_v4/manifest.json,outputs/exp_kg_call_cap_v4/manifest.json \
  --labels cda,call,call_cap \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_kg_robust_v4

python -m p2p.sim.overlay \
  --manifests outputs/exp_opt_v4/manifest.json,outputs/exp_opt_call_v4/manifest.json \
  --labels opt_cda,opt_call \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_opt_robust_v4

python -m p2p.sim.overlay \
  --manifests outputs/exp_kg_v4/manifest.json,outputs/exp_kg_ticker_v4/manifest.json \
  --labels book,ticker \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_kg_ticker_v4

python -m p2p.sim.overlay \
  --manifests outputs/exp_opt_v4/manifest.json,outputs/exp_opt_ticker_v4/manifest.json \
  --labels book,ticker \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_opt_ticker_v4

echo "[6/7] Phase 9 theory checks (Δ acceptance vs τ/K; diminishing returns; ms~offers)"
python -m p2p.sim.theory \
  --manifests outputs/exp_band_v4/manifest.json,outputs/exp_k_v4/manifest.json,outputs/exp_kg_v4/manifest.json \
  --out-dir outputs/analysis/phase9_v4_final

echo "[7/8] Representative figures (final overlays and per-run plots)"
FIG_DIR=outputs/analysis/figs_final
mkdir -p "${FIG_DIR}"

# Publication figures from aggregated CSVs
python -m p2p.sim.plots_final --out-dir ${FIG_DIR}

# k_greedy (N=500, K=5, seed=1000)
python -m p2p.sim.analysis_cli \
  --interval-csv outputs/exp_kg_v4/N500_satisficer_k_greedy_tauNone_K5_s1000/interval_metrics_N500_satisficer_k_greedy_tauNone_K5_s1000.csv \
  --decision-csv outputs/exp_kg_v4/N500_satisficer_k_greedy_tauNone_K5_s1000/decision_metrics_N500_satisficer_k_greedy_tauNone_K5_s1000.csv \
  --out-dir ${FIG_DIR}

# optimizer (N=500, seed=1000)
python -m p2p.sim.analysis_cli \
  --interval-csv outputs/exp_opt_v4/N500_optimizer_na_tauNone_KNone_s1000/interval_metrics_N500_optimizer_na_tauNone_KNone_s1000.csv \
  --decision-csv outputs/exp_opt_v4/N500_optimizer_na_tauNone_KNone_s1000/decision_metrics_N500_optimizer_na_tauNone_KNone_s1000.csv \
  --out-dir ${FIG_DIR}

# band (N=500, tau=10, seed=1000)
python -m p2p.sim.analysis_cli \
  --interval-csv outputs/exp_band_v4/N500_satisficer_band_tau10_KNone_s1000/interval_metrics_N500_satisficer_band_tau10_KNone_s1000.csv \
  --decision-csv outputs/exp_band_v4/N500_satisficer_band_tau10_KNone_s1000/decision_metrics_N500_satisficer_band_tau10_KNone_s1000.csv \
  --out-dir ${FIG_DIR}

# k_search (N=500, K=3, seed=1000)
python -m p2p.sim.analysis_cli \
  --interval-csv outputs/exp_k_v4/N500_satisficer_k_search_tauNone_K3_s1000/interval_metrics_N500_satisficer_k_search_tauNone_K3_s1000.csv \
  --decision-csv outputs/exp_k_v4/N500_satisficer_k_search_tauNone_K3_s1000/decision_metrics_N500_satisficer_k_search_tauNone_K3_s1000.csv \
  --out-dir ${FIG_DIR}

echo "Done. Artifacts under outputs/ and outputs/analysis/."
