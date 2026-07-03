"""Configurable traffic signal with RED, YELLOW, and GREEN phases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SignalColor(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


@dataclass
class TrafficLightConfig:
    """Timing configuration for one traffic signal cycle."""

    green_duration_s: float = 30.0
    yellow_duration_s: float = 3.0
    red_duration_s: float = 30.0
    min_green_s: float = 10.0
    max_green_s: float = 60.0
    all_red_s: float = 2.0

    def __post_init__(self) -> None:
        if self.green_duration_s < self.min_green_s:
            raise ValueError("green_duration_s must be >= min_green_s")
        if self.green_duration_s > self.max_green_s:
            raise ValueError("green_duration_s must be <= max_green_s")
        if self.yellow_duration_s <= 0:
            raise ValueError("yellow_duration_s must be > 0")
        if self.red_duration_s <= 0:
            raise ValueError("red_duration_s must be > 0")
        if self.all_red_s < 0:
            raise ValueError("all_red_s must be >= 0")


@dataclass
class TrafficLightState:
    color: SignalColor
    elapsed_in_phase_s: float
    phase_duration_s: float
    cycle_count: int


class TrafficLight:
    """Fixed-cycle traffic signal with configurable phase timers."""

    _PHASE_SEQUENCE = (SignalColor.GREEN, SignalColor.YELLOW, SignalColor.RED)

    def __init__(self, config: TrafficLightConfig | None = None) -> None:
        self.config = config or TrafficLightConfig()
        self.color = SignalColor.RED
        self.elapsed_in_phase_s = 0.0
        self.cycle_count = 0
        self._all_red_remaining_s = 0.0

    def phase_duration(self, color: SignalColor | None = None) -> float:
        active = color or self.color
        if active is SignalColor.GREEN:
            return self.config.green_duration_s
        if active is SignalColor.YELLOW:
            return self.config.yellow_duration_s
        return self.config.red_duration_s

    def tick(self, delta_s: float) -> TrafficLightState:
        """Advance the signal by one simulation step."""
        if delta_s <= 0:
            raise ValueError("delta_s must be > 0")

        if self._all_red_remaining_s > 0:
            self._all_red_remaining_s = max(0.0, self._all_red_remaining_s - delta_s)
            self.color = SignalColor.RED
            return self.snapshot()

        self.elapsed_in_phase_s += delta_s
        while self.elapsed_in_phase_s >= self.phase_duration():
            self.elapsed_in_phase_s -= self.phase_duration()
            self._advance_phase()

        return self.snapshot()

    def snapshot(self) -> TrafficLightState:
        return TrafficLightState(
            color=self.color,
            elapsed_in_phase_s=self.elapsed_in_phase_s,
            phase_duration_s=self.phase_duration(),
            cycle_count=self.cycle_count,
        )

    def to_dict(self) -> dict:
        state = self.snapshot()
        return {
            "color": state.color.value,
            "elapsed_in_phase_s": round(state.elapsed_in_phase_s, 2),
            "phase_duration_s": round(state.phase_duration_s, 2),
            "cycle_count": state.cycle_count,
            "config": {
                "green_duration_s": self.config.green_duration_s,
                "yellow_duration_s": self.config.yellow_duration_s,
                "red_duration_s": self.config.red_duration_s,
                "min_green_s": self.config.min_green_s,
                "max_green_s": self.config.max_green_s,
                "all_red_s": self.config.all_red_s,
            },
        }

    def _advance_phase(self) -> None:
        current_index = self._PHASE_SEQUENCE.index(self.color)
        next_index = (current_index + 1) % len(self._PHASE_SEQUENCE)
        self.color = self._PHASE_SEQUENCE[next_index]

        if self.color is SignalColor.GREEN and current_index == len(self._PHASE_SEQUENCE) - 1:
            self.cycle_count += 1

        if self.color is SignalColor.RED and self.config.all_red_s > 0:
            self._all_red_remaining_s = self.config.all_red_s
