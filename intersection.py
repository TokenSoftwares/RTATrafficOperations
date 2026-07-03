"""Intersection state storage for detected vehicles."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

from vehicle import Vehicle, count_by_type


@dataclass(frozen=True)
class IntersectionSnapshot:
    intersection_id: str
    vehicle_count: int
    vehicles_by_type: dict[str, int]
    last_updated: float
    tick_count: int


class Intersection:
    """Stores incoming vehicles and exposes the current intersection state."""

    def __init__(self, intersection_id: str) -> None:
        self.intersection_id = intersection_id
        self._incoming_vehicles: list[Vehicle] = []
        self._last_updated = time.time()
        self._tick_count = 0

    @property
    def incoming_vehicles(self) -> tuple[Vehicle, ...]:
        return tuple(self._incoming_vehicles)

    @property
    def vehicle_count(self) -> int:
        return len(self._incoming_vehicles)

    def store_vehicles(self, vehicles: Sequence[Vehicle]) -> int:
        """Append newly detected vehicles to the intersection."""
        added = list(vehicles)
        self._incoming_vehicles.extend(added)
        self._last_updated = time.time()
        return len(added)

    def clear_vehicles(self) -> None:
        self._incoming_vehicles.clear()
        self._last_updated = time.time()

    def update(self, *, timestamp: float | None = None) -> IntersectionSnapshot:
        """Refresh intersection state for the current simulation tick."""
        self._tick_count += 1
        self._last_updated = timestamp if timestamp is not None else time.time()
        return self.snapshot()

    def snapshot(self) -> IntersectionSnapshot:
        return IntersectionSnapshot(
            intersection_id=self.intersection_id,
            vehicle_count=self.vehicle_count,
            vehicles_by_type=count_by_type(self._incoming_vehicles),
            last_updated=self._last_updated,
            tick_count=self._tick_count,
        )

    def to_dict(self) -> dict:
        state = self.snapshot()
        return {
            "intersection_id": state.intersection_id,
            "vehicle_count": state.vehicle_count,
            "vehicles_by_type": state.vehicles_by_type,
            "last_updated": state.last_updated,
            "tick_count": state.tick_count,
        }
