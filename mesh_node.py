"""Mesh node for exchanging local traffic state with neighboring intersections."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from mesh_protocol import (
    ConnectionState,
    ConnectionStatus,
    EmergencyBroadcastPayload,
    MeshMessage,
    MeshNetwork,
    MeshProtocolConfig,
    MessageType,
    QueueUpdatePayload,
)
from queue_estimator import QueueEstimate


@dataclass(frozen=True)
class NeighborTrafficState:
    neighbor_id: str
    queue_update: QueueUpdatePayload
    received_at: float


@dataclass(frozen=True)
class EmergencyAlert:
    source_node: str
    emergency_phase: str
    reason: str
    received_at: float
    authenticated: bool


@dataclass
class MeshNode:
    """Exchange summarized local traffic information with direct neighbors only."""

    node_id: str
    neighbors: tuple[str, ...]
    network: MeshNetwork
    config: MeshProtocolConfig = field(default_factory=MeshProtocolConfig)
    _connections: dict[str, ConnectionState] = field(default_factory=dict, init=False)
    _neighbor_queue_state: dict[str, NeighborTrafficState] = field(default_factory=dict, init=False)
    _emergency_alerts: list[EmergencyAlert] = field(default_factory=list, init=False)
    _message_log: list[MeshMessage] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        unknown = set(self.neighbors)
        if self.node_id in unknown:
            raise ValueError("A node cannot list itself as a neighbor.")
        for neighbor_id in self.neighbors:
            self._connections[neighbor_id] = ConnectionState(
                local_node=self.node_id,
                remote_node=neighbor_id,
            )

    def connect_to_neighbors(self) -> None:
        """Start TCP-style handshakes with each direct neighbor."""
        for neighbor_id in self.neighbors:
            connection = self._connections[neighbor_id]
            if connection.status is ConnectionStatus.ESTABLISHED:
                continue
            connection.status = ConnectionStatus.SYN_SENT
            connection.last_updated = self.network.clock
            message = self.network.create_message(
                MessageType.SYN,
                self.node_id,
                neighbor_id,
                payload={"handshake": "open"},
            )
            self.network.send(message)
            self._message_log.append(message)

    def publish_queue_update(self, queue_estimate: QueueEstimate) -> int:
        """Share local queue information with established neighbors only."""
        payload = QueueUpdatePayload(
            intersection_id=queue_estimate.intersection_id,
            queue_lengths=dict(queue_estimate.queue_lengths),
            lane_occupancy=dict(queue_estimate.lane_occupancy),
            congestion_level=queue_estimate.congestion_level.value,
            total_vehicles=queue_estimate.total_vehicles,
            busiest_approach=queue_estimate.busiest_approach,
            timestamp=time.time(),
        ).to_dict()

        sent_count = 0
        for neighbor_id in self._established_neighbors():
            message = self.network.create_message(
                MessageType.QUEUE_UPDATE,
                self.node_id,
                neighbor_id,
                payload=payload,
            )
            self.network.send(message)
            self._message_log.append(message)
            sent_count += 1
        return sent_count

    def broadcast_emergency(self, emergency_phase: str, reason: str, *, authenticated: bool = True) -> int:
        """Broadcast an emergency corridor alert to direct neighbors."""
        payload = EmergencyBroadcastPayload(
            source_node=self.node_id,
            emergency_phase=emergency_phase,
            reason=reason,
            timestamp=time.time(),
            authenticated=authenticated,
        ).to_dict()

        sent_count = 0
        for neighbor_id in self.neighbors:
            message = self.network.create_message(
                MessageType.EMERGENCY_BROADCAST,
                self.node_id,
                neighbor_id,
                payload=payload,
            )
            self.network.send(message)
            self._message_log.append(message)
            sent_count += 1
        return sent_count

    def process_inbound(self) -> int:
        """Process all delivered messages waiting in this node's inbox."""
        processed = 0
        for message in self.network.poll_inbox(self.node_id):
            self._handle_message(message)
            processed += 1
        return processed

    def neighbor_queue_states(self) -> dict[str, NeighborTrafficState]:
        return dict(self._neighbor_queue_state)

    def emergency_alerts(self) -> tuple[EmergencyAlert, ...]:
        return tuple(self._emergency_alerts)

    def connection_status(self) -> dict[str, str]:
        return {
            neighbor_id: connection.status.value
            for neighbor_id, connection in self._connections.items()
        }

    def message_log(self) -> tuple[MeshMessage, ...]:
        return tuple(self._message_log)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "neighbors": list(self.neighbors),
            "connections": self.connection_status(),
            "neighbor_queue_states": {
                neighbor_id: {
                    "queue_lengths": state.queue_update.queue_lengths,
                    "congestion_level": state.queue_update.congestion_level,
                    "total_vehicles": state.queue_update.total_vehicles,
                    "received_at": state.received_at,
                }
                for neighbor_id, state in self._neighbor_queue_state.items()
            },
            "emergency_alerts": [
                {
                    "source_node": alert.source_node,
                    "emergency_phase": alert.emergency_phase,
                    "reason": alert.reason,
                    "received_at": alert.received_at,
                    "authenticated": alert.authenticated,
                }
                for alert in self._emergency_alerts
            ],
        }

    def _established_neighbors(self) -> list[str]:
        return [
            neighbor_id
            for neighbor_id, connection in self._connections.items()
            if connection.status is ConnectionStatus.ESTABLISHED
        ]

    def _handle_message(self, message: MeshMessage) -> None:
        self._message_log.append(message)

        if message.message_type is MessageType.SYN:
            self._handle_syn(message)
        elif message.message_type is MessageType.SYN_ACK:
            self._handle_syn_ack(message)
        elif message.message_type is MessageType.ACK:
            self._handle_ack(message)
        elif message.message_type is MessageType.QUEUE_UPDATE:
            self._handle_queue_update(message)
        elif message.message_type is MessageType.EMERGENCY_BROADCAST:
            self._handle_emergency(message)

    def _handle_syn(self, message: MeshMessage) -> None:
        neighbor_id = message.source_node
        connection = self._connections[neighbor_id]

        syn_ack = self.network.create_message(
            MessageType.SYN_ACK,
            self.node_id,
            neighbor_id,
            payload={"handshake": "acknowledge"},
        )
        self.network.send(syn_ack)
        self._message_log.append(syn_ack)

        if connection.status is ConnectionStatus.SYN_SENT:
            # Simultaneous open: both nodes initiated the handshake.
            connection.status = ConnectionStatus.ESTABLISHED
        else:
            connection.status = ConnectionStatus.SYN_RECEIVED
        connection.last_updated = self.network.clock

    def _handle_syn_ack(self, message: MeshMessage) -> None:
        neighbor_id = message.source_node
        connection = self._connections[neighbor_id]
        if connection.status in (ConnectionStatus.SYN_SENT, ConnectionStatus.SYN_RECEIVED):
            ack = self.network.create_message(
                MessageType.ACK,
                self.node_id,
                neighbor_id,
                payload={"handshake": "complete"},
            )
            self.network.send(ack)
            self._message_log.append(ack)
            connection.status = ConnectionStatus.ESTABLISHED
            connection.last_updated = self.network.clock

    def _handle_ack(self, message: MeshMessage) -> None:
        neighbor_id = message.source_node
        connection = self._connections[neighbor_id]
        connection.status = ConnectionStatus.ESTABLISHED
        connection.last_updated = self.network.clock

    def _handle_queue_update(self, message: MeshMessage) -> None:
        if message.source_node not in self.neighbors:
            return

        queue_update = QueueUpdatePayload.from_dict(message.payload)
        self._neighbor_queue_state[message.source_node] = NeighborTrafficState(
            neighbor_id=message.source_node,
            queue_update=queue_update,
            received_at=self.network.clock,
        )

    def _handle_emergency(self, message: MeshMessage) -> None:
        if message.source_node not in self.neighbors:
            return

        payload = EmergencyBroadcastPayload.from_dict(message.payload)
        self._emergency_alerts.append(
            EmergencyAlert(
                source_node=payload.source_node,
                emergency_phase=payload.emergency_phase,
                reason=payload.reason,
                received_at=self.network.clock,
                authenticated=payload.authenticated,
            )
        )
