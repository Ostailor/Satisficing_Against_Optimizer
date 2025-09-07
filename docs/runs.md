Band v3:
python -m p2p.sim.exp_runner --agent satisficer --mode band --N 50,100,200,500 --tau 1,5,10,20 --seeds 5 --intervals 288 --mechanism cda --info-set book --instrument-decisions --out outputs/exp_band_v3


K‑search v3:
python -m p2p.sim.exp_runner --agent satisficer --mode k_search --N 50,100,200,500 --K 1,3,5 --seeds 5 --intervals 288 --mechanism cda --info-set book --instrument-decisions --out outputs/exp_k_v3


K‑greedy v3:
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy --N 50,100,200,500 --K 1,3,5 --seeds 5 --intervals 288 --mechanism cda --info-set book --instrument-decisions --out outputs/exp_kg_v3


Optimizer (greedy/single):
python -m p2p.sim.exp_runner --agent optimizer --optimizer-mode greedy --N 50,100,200,500 --seeds 5 --intervals 288 --mechanism cda --info-set book --instrument-decisions --out outputs/exp_opt_v3


python -m p2p.sim.exp_runner --agent optimizer --optimizer-mode single --N 50,100,200,500 --seeds 5 --intervals 288 --mechanism cda --info-set book --instrument-decisions --out outputs/exp_opt_single_v3


Call auction (no cap):
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy --N 100,200 --K 1,3,5 --seeds 5 --intervals 288 --mechanism call --info-set book --instrument-decisions --out outputs/exp_kg_call_v3


Call auction (feeder cap, e.g., 500 kW):
python -m p2p.sim.exp_runner --agent satisficer --mode k_greedy --N 100,200 --K 1,3,5 --seeds 5 --intervals 288 --mechanism call --feeder-cap 500 --info-set book --instrument-decisions --out outputs/exp_kg_call_cap_v3


Optimizer under call:
python -m p2p.sim.exp_runner --agent optimizer --optimizer-mode greedy --N 100,200 --seeds 5 --intervals 288 --mechanism call --info-set book --instrument-decisions --out outputs/exp_opt_call_v3


Aggregate and overlay (Phase 7 artifacts)

Per experiment:
python -m p2p.sim.aggregate --manifest outputs/exp_band_v3/manifest.json --out-dir outputs/analysis/exp_band_v3 --pareto-groupby N

Repeat for exp_k_v3, exp_kg_v3, exp_opt_v3, and any call-auction runs.


Combined overlay:
python -m p2p.sim.overlay --manifests outputs/exp_band_v3/manifest.json,outputs/exp_k_v3/manifest.json,outputs/exp_kg_v3/manifest.json,outputs/exp_opt_v3/manifest.json --labels band,k_search,k_greedy,opt_greedy --pareto-groupby N --out-dir outputs/analysis/overlay_v3
