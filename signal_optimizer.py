"""Signal timing decisions based on intersection queue state."""

from __future__ import annotations

from dataclasses import dataclass

from intersection import Intersection
from queue_estimator import APPROACH_NAMES, CongestionLevel, QueueEstimate, QueueEstimator


@dataclass(frozen=True)
class SignalDecision:
    """Recommended signal action produced by the optimizer (decision only)."""

    intersection_id: str
    next_phase: str
    green_duration_s: float
    skip_phase: bool
    congestion_level: CongestionLevel
    queue_estimate: QueueEstimate
    rationale: str

    def to_dict(self) -> dict:
        return {
            "intersection_id": self.intersection_id,
            "next_phase": self.next_phase,
            "green_duration_s": round(self.green_duration_s, 2),
            "skip_phase": self.skip_phase,
            "congestion_level": self.congestion_level.value,
            "queue_estimate": self.queue_estimate.to_dict(),
            "rationale": self.rationale,
        }


@dataclass
class SignalOptimizerConfig:
    min_green_s: float = 10.0
    max_green_s: float = 60.0
    seconds_per_queued_vehicle: float = 2.0
    empty_phase_green_s: float = 10.0


class SignalOptimizer:
    """Read intersection state and decide the next phase and green duration."""

    def __init__(
        self,
        queue_estimator: QueueEstimator | None = None,
        config: SignalOptimizerConfig | None = None,
    ) -> None:
        self.queue_estimator = queue_estimator or QueueEstimator()
        self.config = config or SignalOptimizerConfig()
        self._phase_rotation = list(APPROACH_NAMES)
        self._last_served_phase: str | None = None

    def decide(
        self,
        intersection: Intersection,
        *,
        frame_width: float | None = None,
        frame_height: float | None = None,
    ) -> SignalDecision:
        """Produce a signal decision from the current intersection state."""
        queue_estimate = self.queue_estimator.estimate(
            intersection.intersection_id,
            intersection.incoming_vehicles,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        return self._decide_from_estimate(queue_estimate)

    def decide_from_estimate(self, queue_estimate: QueueEstimate) -> SignalDecision:
        """Produce a signal decision from a precomputed queue estimate."""
        return self._decide_from_estimate(queue_estimate)

    def _decide_from_estimate(self, queue_estimate: QueueEstimate) -> SignalDecision:
        next_phase, skip_phase, rationale = self._select_phase(queue_estimate)
        green_duration_s = self._green_duration(next_phase, queue_estimate, skip_phase)

        return SignalDecision(
            intersection_id=queue_estimate.intersection_id,
            next_phase=next_phase,
            green_duration_s=green_duration_s,
            skip_phase=skip_phase,
            congestion_level=queue_estimate.congestion_level,
            queue_estimate=queue_estimate,
            rationale=rationale,
        )

    def _select_phase(self, estimate: QueueEstimate) -> tuple[str, bool, str]:
        non_empty = [
            approach
            for approach in APPROACH_NAMES
            if estimate.queue_lengths[approach] > 0
        ]

        if not non_empty:
            next_phase = self._rotate_phase()
            return (
                next_phase,
                True,
                f"No vehicles detected on any approach; recommend skipping {next_phase} with minimum green.",
            )

        max_queue = max(estimate.queue_lengths[approach] for approach in non_empty)
        candidates = [approach for approach in non_empty if estimate.queue_lengths[approach] == max_queue]
        next_phase = candidates[0]
        self._last_served_phase = next_phase

        if max_queue == 1:
            rationale = f"Serving {next_phase} with short green for a single queued vehicle."
        else:
            rationale = (
                f"Serving {next_phase} with extended green because it has the longest queue "
                f"({max_queue} vehicles)."
            )
        return next_phase, False, rationale

    def _green_duration(
        self,
        phase: str,
        estimate: QueueEstimate,
        skip_phase: bool,
    ) -> float:
        if skip_phase:
            return self.config.empty_phase_green_s

        queue_length = estimate.queue_lengths[phase]
        if queue_length == 0:
            return self.config.empty_phase_green_s

        proposed = self.config.min_green_s + (queue_length * self.config.seconds_per_queued_vehicle)
        return max(self.config.min_green_s, min(self.config.max_green_s, proposed))

    def _rotate_phase(self) -> str:
        if self._last_served_phase is None:
            self._last_served_phase = self._phase_rotation[0]
            return self._last_served_phase

        current_index = self._phase_rotation.index(self._last_served_phase)
        next_index = (current_index + 1) % len(self._phase_rotation)
        self._last_served_phase = self._phase_rotation[next_index]
        return self._last_served_phase
