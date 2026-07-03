"""Queue estimation from detected vehicles at an intersection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from vehicle import Vehicle


APPROACH_NAMES = ("north", "south", "east", "west")


class CongestionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class QueueEstimate:
    intersection_id: str
    queue_lengths: dict[str, int]
    lane_occupancy: dict[str, float]
    congestion_level: CongestionLevel
    total_vehicles: int
    busiest_approach: str
    frame_width: float
    frame_height: float

    def to_dict(self) -> dict:
        return {
            "intersection_id": self.intersection_id,
            "queue_lengths": self.queue_lengths,
            "lane_occupancy": self.lane_occupancy,
            "congestion_level": self.congestion_level.value,
            "total_vehicles": self.total_vehicles,
            "busiest_approach": self.busiest_approach,
            "frame_width": round(self.frame_width, 1),
            "frame_height": round(self.frame_height, 1),
        }


@dataclass
class QueueEstimatorConfig:
    """Capacity and congestion thresholds for each approach lane."""

    vehicles_per_approach_capacity: int = 20
    low_occupancy_threshold: float = 0.33
    high_occupancy_threshold: float = 0.66
    default_frame_width: float = 640.0
    default_frame_height: float = 640.0


class QueueEstimator:
    """Estimate queue length, lane occupancy, and congestion from Vehicle objects."""

    def __init__(self, config: QueueEstimatorConfig | None = None) -> None:
        self.config = config or QueueEstimatorConfig()

    def estimate(
        self,
        intersection_id: str,
        vehicles: Sequence[Vehicle],
        *,
        frame_width: float | None = None,
        frame_height: float | None = None,
    ) -> QueueEstimate:
        width, height = self._resolve_frame_size(vehicles, frame_width, frame_height)
        queue_lengths = {approach: 0 for approach in APPROACH_NAMES}

        for vehicle in vehicles:
            approach = self._assign_approach(vehicle, width, height)
            queue_lengths[approach] += 1

        lane_occupancy = {
            approach: self._occupancy(count)
            for approach, count in queue_lengths.items()
        }
        congestion_level = self._congestion_level(lane_occupancy.values())
        busiest_approach = max(queue_lengths, key=lambda name: (queue_lengths[name], -APPROACH_NAMES.index(name)))

        return QueueEstimate(
            intersection_id=intersection_id,
            queue_lengths=queue_lengths,
            lane_occupancy=lane_occupancy,
            congestion_level=congestion_level,
            total_vehicles=len(vehicles),
            busiest_approach=busiest_approach,
            frame_width=width,
            frame_height=height,
        )

    def _resolve_frame_size(
        self,
        vehicles: Sequence[Vehicle],
        frame_width: float | None,
        frame_height: float | None,
    ) -> tuple[float, float]:
        if frame_width and frame_height:
            return frame_width, frame_height

        if not vehicles:
            return self.config.default_frame_width, self.config.default_frame_height

        max_x = max(vehicle.bbox[2] for vehicle in vehicles)
        max_y = max(vehicle.bbox[3] for vehicle in vehicles)
        width = frame_width or max(max_x, self.config.default_frame_width)
        height = frame_height or max(max_y, self.config.default_frame_height)
        return width, height

    def _assign_approach(self, vehicle: Vehicle, width: float, height: float) -> str:
        center_x, center_y = vehicle.center
        norm_x = center_x / width
        norm_y = center_y / height

        distances = {
            "north": norm_y,
            "south": 1.0 - norm_y,
            "west": norm_x,
            "east": 1.0 - norm_x,
        }
        return min(distances, key=distances.get)

    def _occupancy(self, queue_length: int) -> float:
        capacity = max(1, self.config.vehicles_per_approach_capacity)
        return min(1.0, queue_length / capacity)

    def _congestion_level(self, occupancies: Sequence[float]) -> CongestionLevel:
        peak = max(occupancies, default=0.0)
        if peak >= self.config.high_occupancy_threshold:
            return CongestionLevel.HIGH
        if peak >= self.config.low_occupancy_threshold:
            return CongestionLevel.MEDIUM
        return CongestionLevel.LOW
