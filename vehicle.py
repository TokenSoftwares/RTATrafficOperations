"""Traffic-domain vehicle types.

Computer vision produces :class:`Vehicle` objects via :mod:`traffic_detection`.
All traffic-management modules should import ``Vehicle`` from here.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from traffic_detection import Vehicle

__all__ = ["Vehicle", "count_by_type", "vehicle_types"]


def count_by_type(vehicles: Sequence[Vehicle]) -> dict[str, int]:
    """Return vehicle counts grouped by type."""
    return dict(Counter(vehicle.type for vehicle in vehicles))


def vehicle_types(vehicles: Sequence[Vehicle]) -> tuple[str, ...]:
    """Return the distinct vehicle types present in a detection batch."""
    return tuple(sorted({vehicle.type for vehicle in vehicles}))
