⚡️ Satisficing vs Optimizing Agents in Peer‑to‑Peer Electricity CDAs

![python](https://img.shields.io/badge/python-3.11-blue.svg)
![license](https://img.shields.io/badge/license-MIT-green.svg)
![reproducibility](https://img.shields.io/badge/reproducible-%E2%9C%93-success)

> Agent‑based P2P electricity market simulator with a 5‑minute continuous double auction (CDA). We compare optimizing agents to lightweight satisficers, measuring both market welfare and per‑agent compute.

Summary
- In sufficiently thick markets (e.g., N ∈ {200, 500}), a simple limited‑search satisficer achieves near‑optimizer welfare (≈100–103% of optimizer’s normalized welfare in our runs) while using ≫ less per‑agent compute.

Repository Structure
- `p2p/market/`: order book and clearing (price‑time priority; maker‑price rule).
- `p2p/agents/`: agent implementations (optimizer; satisficers: τ‑band, K‑search/greedy; baselines: ZI‑C, learner).
- `p2p/sim/`: experiment runner, metrics, aggregation, overlays, plotting, theory checks.
- `outputs/`: generated CSVs and figures (created by scripts below).
- `docs/`: LaTeX paper (`docs/paper.tex`) and references.

Requirements
- Python 3.11
- Install dependencies: `pip install -r requirements.txt`
- Optional (local paper build): a LaTeX distribution with pdflatex + bibtex.

Table of Contents
- [Quick Start](#quick-start-smoke-test)
- [Reproduce Main Results](#reproduce-main-results-v4)
- [Outputs](#outputs-where-to-look)
- [Figure Gallery](#figure-gallery)
- [Paper](#paper-optional)
- [Data & Integrity](#data--integrity)
- [Citing](#citing)
- [License](#license)

Quick Start (smoke test)
- Run a tiny smoke: `python -m p2p.sim.run --smoke --intervals 2 --agents 4`
- Run tests and static checks: `pytest -q && ruff check . && mypy p2p`

Reproduce Main Results (v4)
- Full pipeline (experiments → aggregation → overlays → figures):
  - `bash scripts/run_final_v4.sh`
  - This archives any existing `outputs/` to `outputs_YYYYMMDD-HHMMSS/` and regenerates everything.
- From existing outputs only (overlays + figures):
  - `bash scripts/repro_figs_v4.sh`
  - Add `--full` to rerun the entire pipeline first: `bash scripts/repro_figs_v4.sh --full`

Outputs (where to look)
- Aggregated CSVs: `outputs/analysis/**`
- Final figures: `outputs/analysis/figs_final/`, including:
  - `frontier_overlay_cda.png` — normalized welfare Ŵ vs per‑agent ms.
  - `ratio_to_optimizer.png` — R_W = W_sat / W_opt vs per‑agent ms (0.90–0.98 band shaded).
  - `connector_overlay.png` — Ŵ axes with optimizer→satisficer connectors annotated by R_W.
  - `frontier_and_ratio.png` — two‑panel small multiples (planner‑bound and ratio views).

Data & Integrity
- Each experiment directory contains a `manifest.json` (config, seeds, environment, git hash).
- Overlays and figures are derived from these manifests; analysis keeps all runs and reports bootstrap CIs across seeds.

Citing
- If you use this code or results, please cite the accompanying paper:
  - Om Tailor, “Satisficing Agents Achieve Near‑Optimal Welfare with Orders‑of‑Magnitude Lower Compute in Peer‑to‑Peer Electricity Markets,” 2025. (See `paper.pdf`.)
  - A DOI will be added here once a release is archived (e.g., Zenodo).
  
  BibTeX (placeholder):
  ```bibtex
  @misc{tailor2025satisficing,
    author = {Tailor, Om},
    title = {Satisficing Agents Achieve Near-Optimal Welfare with Orders-of-Magnitude Lower Compute in Peer-to-Peer Electricity Markets},
    year = {2025},
    howpublished = {arXiv/Working paper},
    note = {See repository docs/paper.tex}
  }
  ```

License
- MIT

Releases (for dataset/DOI)
- Package artifacts for a release: `bash scripts/package_release_artifacts.sh`
- Produces `dist/` tarballs: manifests, analysis CSVs, and figures, plus SHA‑256 checksums.
