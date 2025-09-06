P2P Market Simulator (CDA): Satisficing vs Optimizing Agents

Overview
- Agent-based P2P electricity market with continuous double auction (CDA) at 5-minute cadence.
- Compare optimizing agents vs satisficing agents on efficiency–compute trade-offs with rigorous instrumentation.

Status
- Phase 1 complete: price–time priority CDA with maker-price rule, partial fills, cancel/modify, and tests.
- Phase 2 complete: load/PV/EV profiles, battery model (no-op dispatch placeholder), per-interval energy tests.

Quickstart
- Smoke run: `python -m p2p.sim.run --smoke --intervals 2 --agents 4`
- Run tests: `pytest -q`
- Lint/type: `ruff check . && mypy p2p`

Code layout
- `p2p/market/`: order book and clearing logic.
- `p2p/agents/`: base prosumer + strategy stubs (optimizer, satisficer, ZI, learner).
- `p2p/env/`: profiles (load, PV) and device models (battery, EV charging).
- `p2p/sim/`: runner, metrics, profiling utility.

License
- MIT
