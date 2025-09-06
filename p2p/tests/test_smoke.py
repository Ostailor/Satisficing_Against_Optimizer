from __future__ import annotations

from p2p.sim.run import run_smoke


def test_smoke_run_basic() -> None:
    summary = run_smoke(intervals=2, n_agents=4)
    assert summary.intervals == 2
    assert summary.agents == 4
    # Expect some posted volume in the no-op market
    assert summary.posted_volume_kwh > 0.0

