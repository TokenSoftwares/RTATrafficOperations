"""End-to-end capstone demo simulator wiring all traffic modules together."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from central_hub import CentralHub
from demo_scenarios import DemoScenario, ScenarioName, get_scenario, list_scenarios
from edge_node import EdgeNode
from mesh_node import MeshNode
from mesh_protocol import MeshNetwork, MeshProtocolConfig
from queue_estimator import QueueEstimate, QueueEstimator
from safety_kernel import (
    ApprovedSignalDecision,
    EmergencyOverride,
    RejectedSignalDecision,
    SafetyContext,
    SafetyKernel,
    SafetyValidationResult,
    is_approved,
)
from signal_optimizer import SignalDecision, SignalOptimizer
from traffic_light import SignalColor, TrafficLightConfig


FRAME_SIZE = 640.0


@dataclass
class NodeRuntime:
    edge: EdgeNode
    mesh: MeshNode
    safety_context: SafetyContext = field(default_factory=SafetyContext)
    active_phase: str | None = None
    last_queue_estimate: QueueEstimate | None = None
    last_decision: SignalDecision | None = None
    last_validation: SafetyValidationResult | None = None


class DemoSimulator:
    """Runs the full local demo loop for three connected intersections."""

    def __init__(self) -> None:
        self.hub = CentralHub()
        self.network = MeshNetwork(MeshProtocolConfig(latency_ms=80, jitter_ms=0))
        self.queue_estimator = QueueEstimator()
        self.optimizer = SignalOptimizer()
        self.safety_kernel = SafetyKernel()
        self.nodes: dict[str, NodeRuntime] = {}
        self.current_scenario: DemoScenario = get_scenario(ScenarioName.NORMAL.value)
        self._lock = threading.RLock()
        self._tick_count = 0
        self._running = False
        self._thread: threading.Thread | None = None
        self._build_nodes()

    def _build_nodes(self) -> None:
        light_config = TrafficLightConfig(
            green_duration_s=20.0,
            yellow_duration_s=3.0,
            red_duration_s=20.0,
            min_green_s=10.0,
            max_green_s=60.0,
            all_red_s=2.0,
        )
        topology = {
            "J1": ("J2",),
            "J2": ("J1", "J3"),
            "J3": ("J2",),
        }
        self.nodes = {}
        for node_id, neighbors in topology.items():
            edge = EdgeNode(node_id, traffic_light_config=light_config)
            mesh = MeshNode(node_id, neighbors, self.network)
            self.nodes[node_id] = NodeRuntime(edge=edge, mesh=mesh)

        for runtime in self.nodes.values():
            runtime.mesh.connect_to_neighbors()
        for _ in range(6):
            self.network.step()
            for runtime in self.nodes.values():
                runtime.mesh.process_inbound()

    def start(self, interval_s: float = 2.0) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(interval_s,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def set_scenario(self, scenario_key: str) -> DemoScenario:
        with self._lock:
            self.current_scenario = get_scenario(scenario_key)
            for runtime in self.nodes.values():
                runtime.edge.intersection.clear_vehicles()
                runtime.last_queue_estimate = None
                runtime.last_decision = None
                runtime.last_validation = None
            self.run_tick()
            return self.current_scenario

    def run_tick(self) -> None:
        with self._lock:
            self._tick_count += 1
            scenario = self.current_scenario

            for node_id, runtime in self.nodes.items():
                runtime.edge.intersection.clear_vehicles()
                vehicles = scenario.vehicles_for_node(node_id)
                runtime.edge.receive_vehicles(vehicles)

            for node_id, runtime in self.nodes.items():
                self._process_node(node_id, runtime, scenario)

            for _ in range(2):
                self.network.step()
                for runtime in self.nodes.values():
                    runtime.mesh.process_inbound()

    def dashboard_state(self) -> dict:
        with self._lock:
            intersections = []
            for node_id, runtime in self.nodes.items():
                edge = runtime.edge
                queue = runtime.last_queue_estimate
                validation = runtime.last_validation
                intersections.append(
                    {
                        "node_id": node_id,
                        "signal_color": edge.traffic_light.color.value,
                        "active_phase": runtime.active_phase,
                        "vehicle_count": edge.intersection.vehicle_count,
                        "queue_lengths": queue.queue_lengths if queue else {},
                        "congestion_level": queue.congestion_level.value if queue else "LOW",
                        "busiest_approach": queue.busiest_approach if queue else None,
                        "safety_status": self._validation_status(validation),
                        "safety_detail": validation.to_dict() if validation else None,
                        "mesh_connections": runtime.mesh.connection_status(),
                        "emergency_alerts": [
                            {
                                "source_node": alert.source_node,
                                "emergency_phase": alert.emergency_phase,
                                "reason": alert.reason,
                            }
                            for alert in runtime.mesh.emergency_alerts()[-3:]
                        ],
                    }
                )

            mesh_messages = []
            for node_id, runtime in self.nodes.items():
                for message in runtime.mesh.message_log()[-5:]:
                    mesh_messages.append(
                        {
                            "node_id": node_id,
                            **message.to_dict(),
                        }
                    )
            mesh_messages = mesh_messages[-20:]

            return {
                "tick_count": self._tick_count,
                "scenario": {
                    "key": self.current_scenario.key.value,
                    "title": self.current_scenario.title,
                    "description": self.current_scenario.description,
                },
                "scenarios": list_scenarios(),
                "intersections": intersections,
                "mesh_messages": mesh_messages,
                "hub": self.hub.dashboard_snapshot(),
            }

    def _loop(self, interval_s: float) -> None:
        while self._running:
            self.run_tick()
            time.sleep(interval_s)

    def _process_node(self, node_id: str, runtime: NodeRuntime, scenario: DemoScenario) -> None:
        edge = runtime.edge
        queue_estimate = self.queue_estimator.estimate(
            node_id,
            edge.intersection.incoming_vehicles,
            frame_width=FRAME_SIZE,
            frame_height=FRAME_SIZE,
        )
        runtime.last_queue_estimate = queue_estimate

        decision = self.optimizer.decide(edge.intersection, frame_width=FRAME_SIZE, frame_height=FRAME_SIZE)
        if scenario.force_unsafe_green and node_id == "J2":
            decision = self._unsafe_decision(decision)

        emergency_override = None
        if (
            scenario.emergency_node == node_id
            and scenario.emergency_phase
            and scenario.emergency_reason
        ):
            emergency_override = EmergencyOverride(
                phase=scenario.emergency_phase,
                reason=scenario.emergency_reason,
                authenticated=True,
            )

        if scenario.pedestrian_active_node == node_id:
            runtime.safety_context.pedestrian_crossing_active = True
            runtime.safety_context.pedestrian_clearance_remaining_s = 5.0
        else:
            runtime.safety_context.pedestrian_crossing_active = False
            runtime.safety_context.pedestrian_clearance_remaining_s = 0.0

        runtime.safety_context.active_green_phase = runtime.active_phase
        validation = self.safety_kernel.validate(
            decision,
            runtime.safety_context,
            emergency_override=emergency_override,
        )
        runtime.last_decision = decision
        runtime.last_validation = validation

        if is_approved(validation):
            self._apply_approved(runtime, validation)
        else:
            runtime.active_phase = runtime.active_phase or "hold"

        runtime.mesh.publish_queue_update(queue_estimate)
        if emergency_override is not None and is_approved(validation):
            sent = runtime.mesh.broadcast_emergency(
                scenario.emergency_phase or decision.next_phase,
                scenario.emergency_reason or "Emergency corridor",
            )
            self.hub.record_mesh_event(
                {
                    "type": "EMERGENCY_BROADCAST",
                    "source_node": node_id,
                    "sent_to_neighbors": sent,
                    "phase": scenario.emergency_phase,
                }
            )

        for message in runtime.mesh.message_log()[-3:]:
            self.hub.record_mesh_event(
                {
                    "type": message.message_type.value,
                    "source_node": message.source_node,
                    "target_node": message.target_node,
                    "node_context": node_id,
                }
            )

        self.hub.receive_report(
            self.hub.build_report(
                junction_id=node_id,
                traffic_state={
                    "queue_lengths": queue_estimate.queue_lengths,
                    "lane_occupancy": queue_estimate.lane_occupancy,
                    "congestion_level": queue_estimate.congestion_level.value,
                    "total_vehicles": queue_estimate.total_vehicles,
                    "busiest_approach": queue_estimate.busiest_approach,
                },
                ai_decision_summary={
                    "next_phase": decision.next_phase,
                    "green_duration_s": decision.green_duration_s,
                    "skip_phase": decision.skip_phase,
                    "rationale": decision.rationale,
                },
                safety_kernel_status=validation.to_dict(),
                emergency_event=(
                    {
                        "active": emergency_override is not None and is_approved(validation),
                        "phase": scenario.emergency_phase,
                        "reason": scenario.emergency_reason,
                    }
                    if scenario.emergency_node == node_id
                    else None
                ),
                sensor_health=scenario.sensor_health or {"camera": "OK", "mesh": "OK", "v2i": "OK"},
                mesh_summary={
                    "connections": runtime.mesh.connection_status(),
                    "neighbor_count": len(runtime.mesh.neighbor_queue_states()),
                },
            )
        )

        edge.tick(1.0)

    def _apply_approved(self, runtime: NodeRuntime, validation: SafetyValidationResult) -> None:
        assert isinstance(validation, ApprovedSignalDecision)
        edge = runtime.edge
        config = edge.traffic_light.config
        config.green_duration_s = validation.approved_green_duration_s
        config.yellow_duration_s = validation.approved_yellow_duration_s
        config.all_red_s = validation.all_red_clearance_s
        runtime.active_phase = validation.approved_phase
        runtime.safety_context.active_green_phase = validation.approved_phase
        edge.traffic_light.color = SignalColor.GREEN
        edge.traffic_light.elapsed_in_phase_s = 0.0

    def _unsafe_decision(self, decision: SignalDecision) -> SignalDecision:
        return SignalDecision(
            intersection_id=decision.intersection_id,
            next_phase=decision.next_phase,
            green_duration_s=2.0,
            skip_phase=False,
            congestion_level=decision.congestion_level,
            queue_estimate=decision.queue_estimate,
            rationale="Forced unsafe proposal for Safety Kernel demo.",
        )

    @staticmethod
    def _validation_status(validation: SafetyValidationResult | None) -> str:
        if validation is None:
            return "PENDING"
        if isinstance(validation, ApprovedSignalDecision):
            return "APPROVED"
        if isinstance(validation, RejectedSignalDecision):
            return "REJECTED"
        return "UNKNOWN"


_simulator: DemoSimulator | None = None


def get_simulator() -> DemoSimulator:
    global _simulator
    if _simulator is None:
        _simulator = DemoSimulator()
    return _simulator
