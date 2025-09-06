Preregistration — Efficiency–Compute Trade-off (P2P CDA)

Hypotheses
- H1 (Frontier): Satisficers achieve ≥90–98% of optimizer quote-surplus welfare with 10–100× lower per-agent compute.
- H2 (Scaling): Welfare gaps shrink and compute savings grow as N increases.
- H3 (Rules): τ-band and K-search generate a smooth compute–welfare Pareto frontier.
- H4 (Robustness): Results persist under periodic call auction and modest feeder congestion.

Design
- Factors: N ∈ {25,50,100,200}; τ ∈ {1,5,10,20}; K ∈ {1,3,5}; seeds ≥ 30; horizon = 24h.
- Agents: Optimizer, Satisficer (τ, K), baselines (ZI-C, no-regret learner).
- Microstructure: CDA (maker-price rule), periodic call auction (robustness).
- Network: single-feeder capacity {∞, medium, tight} (robustness).

Metrics
- Welfare: quote-based surplus W; normalized Ŵ = W / W_bound (planner bound per interval).
- Energy: curtailment, unserved energy.
- Compute: per-agent wall-clock, offers_seen, solver_calls, learners_steps, peak_mem_MB.

Exclusion Criteria
- Any run with profiling overhead > 3% on smoke calibration is flagged and excluded; such exclusions are reported.
- Simulation crashes: no data deletion; runs marked as failed with logs retained.

Outputs & Integrity
- Manifest per run: cpu_model, cores, python_version, os, git hash, config, seed.
- All CSVs retained; bootstrap CIs; non-dominated frontier extraction.

