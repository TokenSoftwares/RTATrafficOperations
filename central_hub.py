"""Central monitoring hub for finalized edge-node reports."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class HubReport:
    junction_id: str
    timestamp: float
    traffic_state: dict
    ai_decision_summary: dict
    safety_kernel_status: dict
    emergency_event: dict | None
    sensor_health: dict
    mesh_summary: dict

    def to_dict(self) -> dict:
        return {
            "junction_id": self.junction_id,
            "timestamp": self.timestamp,
            "traffic_state": self.traffic_state,
            "ai_decision_summary": self.ai_decision_summary,
            "safety_kernel_status": self.safety_kernel_status,
            "emergency_event": self.emergency_event,
            "sensor_health": self.sensor_health,
            "mesh_summary": self.mesh_summary,
        }


class CentralHub:
    """Monitoring and reporting only. Never creates or approves signal decisions."""

    def __init__(self, hub_id: str = "DUBAI-CENTRAL-HUB") -> None:
        self.hub_id = hub_id
        self._reports: dict[str, HubReport] = {}
        self._report_history: list[HubReport] = []
        self._mesh_events: list[dict] = []

    def receive_report(self, report: HubReport) -> None:
        """Store the latest finalized report from an edge node."""
        self._reports[report.junction_id] = report
        self._report_history.append(report)
        if len(self._report_history) > 200:
            self._report_history = self._report_history[-200:]

    def record_mesh_event(self, event: dict) -> None:
        """Store summarized mesh activity for dashboard monitoring."""
        self._mesh_events.append({**event, "timestamp": time.time()})
        if len(self._mesh_events) > 100:
            self._mesh_events = self._mesh_events[-100:]

    def latest_reports(self) -> dict[str, HubReport]:
        return dict(self._reports)

    def mesh_events(self) -> list[dict]:
        return list(self._mesh_events)

    def dashboard_snapshot(self) -> dict:
        """Read-only aggregate for the dashboard."""
        return {
            "hub_id": self.hub_id,
            "updated_at": time.time(),
            "junction_count": len(self._reports),
            "reports": {node_id: report.to_dict() for node_id, report in self._reports.items()},
            "mesh_events": self.mesh_events()[-20:],
        }

    def build_report(
        self,
        *,
        junction_id: str,
        traffic_state: dict,
        ai_decision_summary: dict,
        safety_kernel_status: dict,
        emergency_event: dict | None = None,
        sensor_health: dict | None = None,
        mesh_summary: dict | None = None,
    ) -> HubReport:
        """Helper for edge simulators to format finalized reports."""
        return HubReport(
            junction_id=junction_id,
            timestamp=time.time(),
            traffic_state=traffic_state,
            ai_decision_summary=ai_decision_summary,
            safety_kernel_status=safety_kernel_status,
            emergency_event=emergency_event,
            sensor_health=sensor_health or {"camera": "OK", "mesh": "OK", "v2i": "OK"},
            mesh_summary=mesh_summary or {},
        )
