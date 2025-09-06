P2P Market Simulator (CDA): Satisficing vs Optimizing Agents

Overview
- Agent-based P2P electricity market with continuous double auction (CDA) at 5-minute cadence.
- Compare optimizing agents vs satisficing agents on efficiency–compute trade-offs with rigorous instrumentation.

Status
- Phase 1 complete: price–time priority CDA with maker-price rule, partial fills, cancel/modify, and tests.
- Phase 2 complete: load/PV/EV profiles, battery model (no-op dispatch placeholder), per-interval energy tests.
- Phase 3 complete: decision rules — satisficer (τ-band and K-search) and optimizer baselines with unit tests.
- Phase 4 complete: decision instrumentation (wall time, offers_seen, solver_calls, memory) with CSV logging and overhead test (<3%).

Quickstart
- Smoke run: `python -m p2p.sim.run --smoke --intervals 2 --agents 4`
- Run tests: `pytest -q`
- Lint/type: `ruff check . && mypy p2p`

Instrumentation (Phase 4)
- Enable instrumentation on smoke runs:
  - `python -m p2p.sim.run --smoke --intervals 2 --agents 4 --instrument --metrics-out outputs/metrics_smoke.csv`
- CSV columns written per agent per interval:
  - `run_id, t, agent_id, agent_type, action_type, price_cperkwh, qty_kwh, offers_seen, solver_calls, learners_steps, wall_ms, mem_mb`
- Overhead check: see `p2p/tests/test_instrumentation.py` (ensures timer overhead < 3%).

Code layout
- `p2p/market/`: order book and clearing logic.
- `p2p/agents/`: prosumer + strategy agents (optimizer, satisficer, ZI, learner).
- `p2p/env/`: profiles (load, PV) and device models (battery, EV charging).
- `p2p/sim/`: runner, metrics, profiling utilities (instrumentation).

Development
- Pre-commit hooks (ruff + mypy + hygiene):
  - `pip install pre-commit`
  - `pre-commit install`
  - Run once on all files: `pre-commit run -a`
- CI runs ruff, mypy, and pytest on every push (see `.github/workflows/ci.yml`).

License
- MIT
