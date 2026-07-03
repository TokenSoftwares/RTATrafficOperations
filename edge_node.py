"""AI Edge Node: owns one traffic light and one intersection."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

from intersection import Intersection, IntersectionSnapshot
from traffic_light import TrafficLight, TrafficLightConfig, TrafficLightState
from vehicle import Vehicle


@dataclass(frozen=True)
class EdgeNodeSnapshot:
    node_id: str
    intersection: IntersectionSnapshot
    traffic_light: TrafficLightState
    last_tick: float


class EdgeNode:
    """Edge node that ingests vehicle detections and advances local state each tick."""

    def __init__(
        self,
        node_id: str,
        *,
        traffic_light: TrafficLight | None = None,
        intersection: Intersection | None = None,
        traffic_light_config: TrafficLightConfig | None = None,
    ) -> None:
        self.node_id = node_id
        self.traffic_light = traffic_light or TrafficLight(traffic_light_config)
        self.intersection = intersection or Intersection(intersection_id=node_id)
        self._last_tick = time.time()

    def receive_vehicles(self, vehicles: Sequence[Vehicle]) -> int:
        """Accept Vehicle objects produced by the detector service."""
        return self.intersection.store_vehicles(vehicles)

    def tick(self, delta_s: float = 1.0) -> EdgeNodeSnapshot:
        """Advance the traffic light and refresh intersection state."""
        if delta_s <= 0:
            raise ValueError("delta_s must be > 0")

        light_state = self.traffic_light.tick(delta_s)
        now = time.time()
        intersection_state = self.intersection.update(timestamp=now)
        self._last_tick = now

        return EdgeNodeSnapshot(
            node_id=self.node_id,
            intersection=intersection_state,
            traffic_light=light_state,
            last_tick=self._last_tick,
        )

    def snapshot(self) -> EdgeNodeSnapshot:
        return EdgeNodeSnapshot(
            node_id=self.node_id,
            intersection=self.intersection.snapshot(),
            traffic_light=self.traffic_light.snapshot(),
            last_tick=self._last_tick,
        )

    def to_dict(self) -> dict:
        state = self.snapshot()
        return {
            "node_id": state.node_id,
            "intersection": self.intersection.to_dict(),
            "traffic_light": self.traffic_light.to_dict(),
            "last_tick": state.last_tick,
        }
