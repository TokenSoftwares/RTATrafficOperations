"""Safety Kernel: validates SignalOptimizer decisions before actuator changes."""

from __future__ import annotations

from dataclasses import dataclass, field

from queue_estimator import APPROACH_NAMES
from signal_optimizer import SignalDecision


@dataclass
class SafetyKernelConfig:
    min_green_s: float = 10.0
    max_green_s: float = 60.0
    min_yellow_s: float = 3.0
    all_red_s: float = 2.0
    pedestrian_clearance_s: float = 7.0
    emergency_override_allowed: bool = True


@dataclass
class SafetyContext:
    """Current intersection safety state used during validation."""

    active_green_phase: str | None = None
    all_red_remaining_s: float = 0.0
    pedestrian_crossing_active: bool = False
    pedestrian_clearance_remaining_s: float = 0.0


@dataclass(frozen=True)
class EmergencyOverride:
    phase: str
    reason: str
    authenticated: bool = True


@dataclass(frozen=True)
class ApprovedSignalDecision:
    decision: SignalDecision
    approved_phase: str
    approved_green_duration_s: float
    approved_yellow_duration_s: float
    all_red_clearance_s: float
    pedestrian_clearance_s: float
    skip_phase: bool
    adjustments: tuple[str, ...] = field(default_factory=tuple)
    emergency_override_applied: bool = False

    def to_dict(self) -> dict:
        return {
            "status": "APPROVED",
            "decision": self.decision.to_dict(),
            "approved_phase": self.approved_phase,
            "approved_green_duration_s": round(self.approved_green_duration_s, 2),
            "approved_yellow_duration_s": round(self.approved_yellow_duration_s, 2),
            "all_red_clearance_s": round(self.all_red_clearance_s, 2),
            "pedestrian_clearance_s": round(self.pedestrian_clearance_s, 2),
            "skip_phase": self.skip_phase,
            "adjustments": list(self.adjustments),
            "emergency_override_applied": self.emergency_override_applied,
        }


@dataclass(frozen=True)
class RejectedSignalDecision:
    decision: SignalDecision
    reason: str
    violation: str

    def to_dict(self) -> dict:
        return {
            "status": "REJECTED",
            "decision": self.decision.to_dict(),
            "reason": self.reason,
            "violation": self.violation,
        }


SafetyValidationResult = ApprovedSignalDecision | RejectedSignalDecision


# Approaches that cannot show green at the same time.
CONFLICT_MATRIX: dict[str, frozenset[str]] = {
    "north": frozenset({"south", "east", "west"}),
    "south": frozenset({"north", "east", "west"}),
    "east": frozenset({"north", "south", "west"}),
    "west": frozenset({"north", "south", "east"}),
}


class SafetyKernel:
    """Validate optimizer decisions against hard-coded safety rules."""

    def __init__(self, config: SafetyKernelConfig | None = None) -> None:
        self.config = config or SafetyKernelConfig()

    def validate(
        self,
        decision: SignalDecision,
        context: SafetyContext | None = None,
        *,
        emergency_override: EmergencyOverride | None = None,
    ) -> SafetyValidationResult:
        """Validate a SignalDecision without creating a new traffic plan."""
        context = context or SafetyContext()
        adjustments: list[str] = []

        if emergency_override is not None and emergency_override.authenticated:
            return self._validate_emergency(decision, emergency_override, adjustments)

        phase_error = self._validate_phase(decision.next_phase)
        if phase_error:
            return self._reject(decision, phase_error, "invalid_phase")

        conflict_error = self._validate_conflicts(decision.next_phase, context)
        if conflict_error:
            return self._reject(decision, conflict_error, "conflicting_green_phase")

        clearance_error = self._validate_clearance_windows(context)
        if clearance_error:
            return self._reject(decision, clearance_error, "clearance_violation")

        pedestrian_error = self._validate_pedestrian_protection(context)
        if pedestrian_error:
            return self._reject(decision, pedestrian_error, "pedestrian_protection")

        green_duration, green_error = self._validate_green_duration(decision.green_duration_s)
        if green_error:
            return self._reject(decision, green_error, "green_duration_bounds")
        if green_duration != decision.green_duration_s:
            adjustments.append(
                f"Capped green duration from {decision.green_duration_s:.2f}s to {green_duration:.2f}s."
            )

        return ApprovedSignalDecision(
            decision=decision,
            approved_phase=decision.next_phase,
            approved_green_duration_s=green_duration,
            approved_yellow_duration_s=self.config.min_yellow_s,
            all_red_clearance_s=self.config.all_red_s,
            pedestrian_clearance_s=self.config.pedestrian_clearance_s,
            skip_phase=decision.skip_phase,
            adjustments=tuple(adjustments),
            emergency_override_applied=False,
        )

    def _validate_emergency(
        self,
        decision: SignalDecision,
        emergency_override: EmergencyOverride,
        adjustments: list[str],
    ) -> SafetyValidationResult:
        if not self.config.emergency_override_allowed:
            return self._reject(
                decision,
                "Emergency override is disabled by Safety Kernel policy.",
                "emergency_override_disabled",
            )

        if not emergency_override.authenticated:
            return self._reject(
                decision,
                "Emergency override request is not authenticated.",
                "emergency_not_authenticated",
            )

        phase_error = self._validate_phase(emergency_override.phase)
        if phase_error:
            return self._reject(decision, phase_error, "invalid_emergency_phase")

        adjustments.append(
            f"Emergency override applied for {emergency_override.phase}: {emergency_override.reason}"
        )
        return ApprovedSignalDecision(
            decision=decision,
            approved_phase=emergency_override.phase,
            approved_green_duration_s=self.config.max_green_s,
            approved_yellow_duration_s=self.config.min_yellow_s,
            all_red_clearance_s=self.config.all_red_s,
            pedestrian_clearance_s=self.config.pedestrian_clearance_s,
            skip_phase=False,
            adjustments=tuple(adjustments),
            emergency_override_applied=True,
        )

    def _validate_phase(self, phase: str) -> str | None:
        if phase not in APPROACH_NAMES:
            return f"Unknown signal phase '{phase}'."
        return None

    def _validate_conflicts(self, proposed_phase: str, context: SafetyContext) -> str | None:
        active_phase = context.active_green_phase
        if active_phase is None:
            return None

        conflicts = CONFLICT_MATRIX.get(proposed_phase, frozenset())
        if active_phase in conflicts:
            return (
                f"Cannot grant green to {proposed_phase} while conflicting phase "
                f"{active_phase} is still active."
            )
        return None

    def _validate_clearance_windows(self, context: SafetyContext) -> str | None:
        if context.all_red_remaining_s > 0:
            return (
                f"All-red clearance is still active ({context.all_red_remaining_s:.2f}s remaining)."
            )
        return None

    def _validate_pedestrian_protection(self, context: SafetyContext) -> str | None:
        if context.pedestrian_crossing_active or context.pedestrian_clearance_remaining_s > 0:
            remaining = context.pedestrian_clearance_remaining_s
            return (
                "Pedestrian crossing clearance is active; vehicle green is blocked until clearance completes."
                + (f" ({remaining:.2f}s remaining)" if remaining > 0 else "")
            )
        return None

    def _validate_green_duration(self, proposed_green_s: float) -> tuple[float, str | None]:
        if proposed_green_s < self.config.min_green_s:
            return proposed_green_s, (
                f"Proposed green duration {proposed_green_s:.2f}s is below minimum "
                f"{self.config.min_green_s:.2f}s."
            )

        if proposed_green_s > self.config.max_green_s:
            return self.config.max_green_s, None

        return proposed_green_s, None

    def _reject(
        self,
        decision: SignalDecision,
        reason: str,
        violation: str,
    ) -> RejectedSignalDecision:
        return RejectedSignalDecision(
            decision=decision,
            reason=reason,
            violation=violation,
        )


def is_approved(result: SafetyValidationResult) -> bool:
    return isinstance(result, ApprovedSignalDecision)
