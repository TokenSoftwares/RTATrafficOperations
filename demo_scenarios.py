"""Predefined runtime scenarios for the capstone demo."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from vehicle import Vehicle


class ScenarioName(str, Enum):
    NORMAL = "normal_traffic"
    RUSH_HOUR = "rush_hour"
    ACCIDENT = "accident"
    EMERGENCY = "emergency_vehicle"
    HEAVY_RAIN = "heavy_rain"


@dataclass(frozen=True)
class DemoScenario:
    key: ScenarioName
    title: str
    description: str
    emergency_node: str | None = None
    emergency_phase: str | None = None
    emergency_reason: str | None = None
    force_unsafe_green: bool = False
    pedestrian_active_node: str | None = None
    sensor_health: dict[str, str] | None = None

    def vehicles_for_node(self, node_id: str) -> tuple[Vehicle, ...]:
        generator = _VEHICLE_GENERATORS[self.key]
        return generator(node_id)


def _vehicle(
    vehicle_id: int,
    vehicle_type: str,
    center_x: float,
    center_y: float,
    confidence: float = 0.9,
) -> Vehicle:
    half = 35.0
    x1, y1 = center_x - half, center_y - half
    x2, y2 = center_x + half, center_y + half
    return Vehicle(
        id=vehicle_id,
        type=vehicle_type,
        confidence=confidence,
        bbox=(x1, y1, x2, y2),
        center=(center_x, center_y),
        timestamp=time.time(),
    )


def _normal_traffic(node_id: str) -> tuple[Vehicle, ...]:
    presets = {
        "J1": [
            _vehicle(0, "car", 320, 80),
            _vehicle(1, "car", 500, 560),
        ],
        "J2": [
            _vehicle(0, "car", 300, 100),
            _vehicle(1, "bus", 520, 520),
        ],
        "J3": [
            _vehicle(0, "car", 340, 90),
        ],
    }
    return tuple(presets.get(node_id, []))


def _rush_hour(node_id: str) -> tuple[Vehicle, ...]:
    presets = {
        "J1": [
            _vehicle(0, "car", 280, 60),
            _vehicle(1, "car", 320, 70),
            _vehicle(2, "car", 360, 85),
            _vehicle(3, "bus", 400, 95),
            _vehicle(4, "truck", 440, 110),
        ],
        "J2": [
            _vehicle(0, "car", 300, 55),
            _vehicle(1, "car", 340, 65),
            _vehicle(2, "car", 380, 75),
            _vehicle(3, "car", 420, 90),
        ],
        "J3": [
            _vehicle(0, "car", 310, 80),
            _vehicle(1, "car", 350, 95),
        ],
    }
    return tuple(presets.get(node_id, []))


def _accident(node_id: str) -> tuple[Vehicle, ...]:
    presets = {
        "J1": [
            _vehicle(0, "car", 320, 90),
        ],
        "J2": [
            _vehicle(0, "car", 300, 70),
            _vehicle(1, "car", 340, 80),
            _vehicle(2, "truck", 60, 320),
            _vehicle(3, "car", 90, 350),
            _vehicle(4, "bus", 560, 300),
            _vehicle(5, "car", 590, 330),
        ],
        "J3": [
            _vehicle(0, "car", 520, 540),
            _vehicle(1, "car", 560, 560),
        ],
    }
    return tuple(presets.get(node_id, []))


def _emergency_vehicle(node_id: str) -> tuple[Vehicle, ...]:
    presets = {
        "J1": [
            _vehicle(0, "truck", 320, 120, confidence=0.88),
            _vehicle(1, "car", 500, 540),
        ],
        "J2": [
            _vehicle(0, "car", 300, 100),
            _vehicle(1, "car", 520, 520),
        ],
        "J3": [
            _vehicle(0, "car", 340, 110),
        ],
    }
    return tuple(presets.get(node_id, []))


def _heavy_rain(node_id: str) -> tuple[Vehicle, ...]:
    # Reduced visibility: fewer detections and lower confidence.
    presets = {
        "J1": [
            _vehicle(0, "car", 320, 80, confidence=0.42),
        ],
        "J2": [
            _vehicle(0, "bus", 300, 90, confidence=0.38),
        ],
        "J3": [],
    }
    return tuple(presets.get(node_id, []))


_VEHICLE_GENERATORS = {
    ScenarioName.NORMAL: _normal_traffic,
    ScenarioName.RUSH_HOUR: _rush_hour,
    ScenarioName.ACCIDENT: _accident,
    ScenarioName.EMERGENCY: _emergency_vehicle,
    ScenarioName.HEAVY_RAIN: _heavy_rain,
}


SCENARIOS: dict[str, DemoScenario] = {
    ScenarioName.NORMAL.value: DemoScenario(
        key=ScenarioName.NORMAL,
        title="Normal Traffic",
        description="Balanced traffic across the corridor with moderate queue lengths.",
    ),
    ScenarioName.RUSH_HOUR.value: DemoScenario(
        key=ScenarioName.RUSH_HOUR,
        title="Rush Hour",
        description="Heavy northbound demand causing congestion at upstream junctions.",
    ),
    ScenarioName.ACCIDENT.value: DemoScenario(
        key=ScenarioName.ACCIDENT,
        title="Accident / Blocked Lane",
        description="Blocked west approach at J2 creates spillback and rerouting pressure.",
        force_unsafe_green=True,
    ),
    ScenarioName.EMERGENCY.value: DemoScenario(
        key=ScenarioName.EMERGENCY,
        title="Emergency Vehicle",
        description="Ambulance V2I priority triggers an emergency corridor request.",
        emergency_node="J1",
        emergency_phase="north",
        emergency_reason="Ambulance V2I priority corridor",
    ),
    ScenarioName.HEAVY_RAIN.value: DemoScenario(
        key=ScenarioName.HEAVY_RAIN,
        title="Heavy Rain",
        description="Reduced camera visibility lowers detection confidence and counts.",
        sensor_health={"camera": "DEGRADED", "mesh": "OK", "v2i": "OK"},
    ),
}


def list_scenarios() -> list[dict]:
    return [
        {
            "key": scenario.key.value,
            "title": scenario.title,
            "description": scenario.description,
        }
        for scenario in SCENARIOS.values()
    ]


def get_scenario(key: str) -> DemoScenario:
    if key not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {key}")
    return SCENARIOS[key]
