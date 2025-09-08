Reproduction and Run Book (v4)

Prereqs
- Python 3.11; install deps: `pip install -r requirements.txt`
- Verified tests: `pytest -q` (should pass). Profiling overhead test target <3%.
- All runs use 5-minute intervals; 288 intervals ≈ one day.

Conventions
- We use v4 output dirs to reflect the finalized instrumentation (single decide() per agent/interval) and satisficer price-time scan.
- Seeds per cell: 5 (`s=1000..1004`). Ns: 50,100,200,500. Adjust as needed for compute budget.

Core CDA (book info) experiments

Optimizer baseline (greedy):
python -m p2p.sim.exp_runner \
  --agent optimizer --optimizer-mode greedy \
  --N 50,100,200,500 --seeds 5 --intervals 288 \
  --mechanism cda --info-set book --instrument-decisions \
  --price-sigma 1.0 \
  --out outputs/exp_opt_v4

Optimizer (single-fill, optional):
python -m p2p.sim.exp_runner \
  --agent optimizer --optimizer-mode single \
  --N 50,100,200,500 --seeds 5 --intervals 288 \
  --mechanism cda --info-set book --instrument-decisions \
  --price-sigma 1.0 \
  --out outputs/exp_opt_single_v4

Satisficer — τ‑band (τ ∈ {1,5,10,20}):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode band --N 50,100,200,500 --tau 1,5,10,20 \
  --seeds 5 --intervals 288 --mechanism cda --info-set book \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_band_v4

Satisficer — K‑search (K ∈ {1,3,5}):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_search --N 50,100,200,500 --K 1,3,5 \
  --seeds 5 --intervals 288 --mechanism cda --info-set book \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_k_v4

Satisficer — K‑greedy (K ∈ {1,3,5}):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_greedy --N 50,100,200,500 --K 1,3,5 \
  --seeds 5 --intervals 288 --mechanism cda --info-set book \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_kg_v4

Robustness experiments

Ticker‑only info set (book vs ticker):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_greedy --N 100,200,500 --K 1,3,5 \
  --seeds 5 --intervals 288 --mechanism cda --info-set ticker \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_kg_ticker_v4

python -m p2p.sim.exp_runner \
  --agent optimizer --optimizer-mode greedy --N 100,200,500 \
  --seeds 5 --intervals 288 --mechanism cda --info-set ticker \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_opt_ticker_v4

Periodic call auction (no feeder cap):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_greedy --N 100,200,500 --K 1,3,5 \
  --seeds 5 --intervals 288 --mechanism call --info-set book \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_kg_call_v4

Periodic call auction (with feeder cap, e.g., 500 kW):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_greedy --N 100,200,500 --K 1,3,5 \
  --seeds 5 --intervals 288 --mechanism call --feeder-cap 500 --info-set book \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_kg_call_cap_v4

python -m p2p.sim.exp_runner \
  --agent optimizer --optimizer-mode greedy --N 100,200,500 \
  --seeds 5 --intervals 288 --mechanism call --info-set book \
  --price-sigma 1.0 \
  --instrument-decisions --out outputs/exp_opt_call_v4

Heterogeneity sweeps (optional)

Band with heterogeneous τ per agent (cycle 1,5,10,20):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode band --N 50,100,200,500 \
  --hetero-tau 1,5,10,20 --seeds 5 --intervals 288 \
  --mechanism cda --info-set book --instrument-decisions \
  --price-sigma 1.0 \
  --out outputs/exp_band_hetero_v4

K‑search with heterogeneous K per agent (cycle 1,3,5):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_search --N 50,100,200,500 \
  --hetero-K 1,3,5 --seeds 5 --intervals 288 \
  --mechanism cda --info-set book --instrument-decisions \
  --price-sigma 1.0 \
  --out outputs/exp_k_hetero_v4

K‑greedy with heterogeneous K per agent (cycle 1,3,5):
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_greedy --N 50,100,200,500 \
  --hetero-K 1,3,5 --seeds 5 --intervals 288 \
  --mechanism cda --info-set book --instrument-decisions \
  --price-sigma 1.0 \
  --out outputs/exp_kg_hetero_v4

“Dated config” cross‑check (higher quote dispersion, mild markups)
- Matches favorable settings from dated runs to verify sensitivity.

Satisficer k_greedy with price_sigma=1.0, buy_markup=0.5, sell_discount=0.5:
python -m p2p.sim.exp_runner \
  --agent satisficer --mode k_greedy --N 50,100,200 \
  --K 1,3,5 --seeds 5 --intervals 288 \
  --mechanism cda --info-set book --instrument-decisions \
  --price-sigma 1.0 --buy-markup 0.5 --sell-discount 0.5 \
  --out outputs/exp_kg_sigma1_v4

Optimizer under same price settings:
python -m p2p.sim.exp_runner \
  --agent optimizer --optimizer-mode greedy --N 50,100,200 \
  --seeds 5 --intervals 288 --mechanism cda --info-set book \
  --instrument-decisions --price-sigma 1.0 --buy-markup 0.5 --sell-discount 0.5 \
  --out outputs/exp_opt_sigma1_v4

Aggregation (frontiers, Pareto, scaling)

Per experiment (repeat for each outputs/exp_*_v4 manifest):
python -m p2p.sim.aggregate \
  --manifest outputs/exp_opt_v4/manifest.json \
  --out-dir outputs/analysis/exp_opt_v4 \
  --pareto-groupby N

Examples to aggregate satisficer variants:
python -m p2p.sim.aggregate --manifest outputs/exp_band_v4/manifest.json --out-dir outputs/analysis/exp_band_v4 --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_k_v4/manifest.json    --out-dir outputs/analysis/exp_k_v4    --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_kg_v4/manifest.json   --out-dir outputs/analysis/exp_kg_v4   --pareto-groupby N

Combined overlay (compare frontiers across experiments)
python -m p2p.sim.overlay \
  --manifests outputs/exp_band_v4/manifest.json,outputs/exp_k_v4/manifest.json,outputs/exp_kg_v4/manifest.json,outputs/exp_opt_v4/manifest.json \
  --labels band,k_search,k_greedy,opt_greedy \
  --pareto-groupby N \
  --out-dir outputs/analysis/overlay_v4

Optional plots per run (price variance, one‑run frontier)
python -m p2p.sim.analysis_cli \
  --interval-csv outputs/exp_kg_v4/N100_satisficer_k_greedy_tauNone_K5_s1000/interval_metrics_N100_satisficer_k_greedy_tauNone_K5_s1000.csv \
  --decision-csv outputs/exp_kg_v4/N100_satisficer_k_greedy_tauNone_K5_s1000/decision_metrics_N100_satisficer_k_greedy_tauNone_K5_s1000.csv \
  --out-dir outputs/analysis/figs_one_run

All‑in‑one (long‑running) script
cat > run_all_v4.sh << 'EOS'
#!/usr/bin/env bash
set -euo pipefail

# Core
python -m p2p.sim.exp_runner --agent optimizer  --optimizer-mode greedy --N 50,100,200,500 --seeds 5 --intervals 288 --mechanism cda  --info-set book --instrument-decisions --price-sigma 1.0 --out outputs/exp_opt_v4
python -m p2p.sim.exp_runner --agent satisficer --mode band      --N 50,100,200,500 --tau 1,5,10,20    --seeds 5 --intervals 288 --mechanism cda  --info-set book --instrument-decisions --price-sigma 1.0 --out outputs/exp_band_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_search  --N 50,100,200,500 --K 1,3,5         --seeds 5 --intervals 288 --mechanism cda  --info-set book --instrument-decisions --price-sigma 1.0 --out outputs/exp_k_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy  --N 50,100,200,500 --K 1,3,5         --seeds 5 --intervals 288 --mechanism cda  --info-set book --instrument-decisions --price-sigma 1.0 --out outputs/exp_kg_v4

# Robustness: ticker and call + cap
python -m p2p.sim.exp_runner --agent optimizer  --optimizer-mode greedy --N 100,200,500 --seeds 5 --intervals 288 --mechanism cda  --info-set ticker --instrument-decisions --price-sigma 1.0 --out outputs/exp_opt_ticker_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy          --N 100,200,500 --K 1,3,5  --seeds 5 --intervals 288 --mechanism cda  --info-set ticker --instrument-decisions --price-sigma 1.0 --out outputs/exp_kg_ticker_v4
python -m p2p.sim.exp_runner --agent optimizer  --optimizer-mode greedy --N 100,200,500 --seeds 5 --intervals 288 --mechanism call --info-set book   --instrument-decisions --price-sigma 1.0 --out outputs/exp_opt_call_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy          --N 100,200,500 --K 1,3,5  --seeds 5 --intervals 288 --mechanism call --info-set book   --instrument-decisions --price-sigma 1.0 --out outputs/exp_kg_call_v4
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy          --N 100,200,500 --K 1,3,5  --seeds 5 --intervals 288 --mechanism call --info-set book --feeder-cap 500 --instrument-decisions --price-sigma 1.0 --out outputs/exp_kg_call_cap_v4

# Aggregation
python -m p2p.sim.aggregate --manifest outputs/exp_opt_v4/manifest.json  --out-dir outputs/analysis/exp_opt_v4  --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_band_v4/manifest.json --out-dir outputs/analysis/exp_band_v4 --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_k_v4/manifest.json    --out-dir outputs/analysis/exp_k_v4    --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_kg_v4/manifest.json   --out-dir outputs/analysis/exp_kg_v4   --pareto-groupby N
python -m p2p.sim.aggregate --manifest outputs/exp_opt_ticker_v4/manifest.json --out-dir outputs/analysis/exp_opt_ticker_v4 --pareto-groupby N || true
python -m p2p.sim.aggregate --manifest outputs/exp_kg_ticker_v4/manifest.json  --out-dir outputs/analysis/exp_kg_ticker_v4  --pareto-groupby N || true
python -m p2p.sim.aggregate --manifest outputs/exp_opt_call_v4/manifest.json   --out-dir outputs/analysis/exp_opt_call_v4   --pareto-groupby N || true
python -m p2p.sim.aggregate --manifest outputs/exp_kg_call_v4/manifest.json    --out-dir outputs/analysis/exp_kg_call_v4    --pareto-groupby N || true
python -m p2p.sim.aggregate --manifest outputs/exp_kg_call_cap_v4/manifest.json --out-dir outputs/analysis/exp_kg_call_cap_v4 --pareto-groupby N || true

# Overlay
python -m p2p.sim.overlay \
  --manifests outputs/exp_band_v4/manifest.json,outputs/exp_k_v4/manifest.json,outputs/exp_kg_v4/manifest.json,outputs/exp_opt_v4/manifest.json \
  --labels band,k_search,k_greedy,opt_greedy --pareto-groupby N \
  --out-dir outputs/analysis/overlay_v4
EOS
chmod +x run_all_v4.sh

Notes
- Compute time is substantial; consider running per block, then aggregating.
- Manifests include env metadata (CPU, OS, Python) and are written per experiment root.
- Frontiers (frontier.csv), Pareto frontiers by N (frontier_pareto_by_N.csv), and scaling.csv are written under `outputs/analysis/...` for each experiment.
- Pricing realism: By default Prosumer draws heterogeneous buy/sell premia per agent (around ~0.5¢, clipped 0–5¢). We keep that heterogeneity for realism. We set `--price-sigma 1.0` to capture intraday quote dispersion; adjust as needed for sensitivity.
