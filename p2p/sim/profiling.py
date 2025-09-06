from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import psutil


def time_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Execute fn and return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result, elapsed_ms


def process_mem_mb() -> float:
    """Return current process RSS in MiB."""
    proc = psutil.Process(os.getpid())
    rss = proc.memory_info().rss
    return rss / (1024 * 1024)
