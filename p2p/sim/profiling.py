from __future__ import annotations

import time
from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def timer() -> Iterator[float]:
    start = time.perf_counter()
    yield start
    _ = time.perf_counter() - start
