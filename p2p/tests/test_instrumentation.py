from __future__ import annotations

import time

from p2p.sim.profiling import time_call


def _work() -> int:
    # Make the baseline heavy enough that wrapper overhead is negligible
    s = 0
    for i in range(100_000):
        s += i * i
    return s


def test_timer_overhead_under_3_percent() -> None:
    # Baseline: call the work many times
    n = 100
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
