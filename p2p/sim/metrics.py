from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunSummary:
    intervals: int
    agents: int
    posted_volume_kwh: float
    traded_volume_kwh: float
