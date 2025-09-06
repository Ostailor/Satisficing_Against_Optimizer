from __future__ import annotations

import time

from p2p.sim.profiling import time_call


def _work() -> int:
    # Sleep-based workload to dominate wrapper overhead while keeping test fast
    time.sleep(0.002)
    return 1


def test_timer_overhead_under_3_percent() -> None:
    # Baseline: call the work many times
    n = 50
    t0 = time.perf_counter()
    for _ in range(n):
        _ = _work()
    baseline = time.perf_counter() - t0

    # Wrapped: use time_call around the same work
    t1 = time.perf_counter()
    for _ in range(n):
        _ = time_call(_work)[0]
    wrapped = time.perf_counter() - t1

    # Compute relative overhead
    overhead = (wrapped - baseline) / baseline if baseline > 0 else 0.0
    assert overhead < 0.03
