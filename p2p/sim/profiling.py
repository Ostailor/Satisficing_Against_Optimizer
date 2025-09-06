from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def timer() -> Iterator[float]:
    start = time.perf_counter()
    yield start
    _ = time.perf_counter() - start
