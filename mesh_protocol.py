"""TCP-style mesh messaging protocol with simulated latency."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    SYN = "SYN"
    SYN_ACK = "SYN_ACK"
    ACK = "ACK"
    QUEUE_UPDATE = "QUEUE_UPDATE"
    EMERGENCY_BROADCAST = "EMERGENCY_BROADCAST"


class ConnectionStatus(str, Enum):
    CLOSED = "CLOSED"
    SYN_SENT = "SYN_SENT"
    SYN_RECEIVED = "SYN_RECEIVED"
    ESTABLISHED = "ESTABLISHED"


@dataclass(frozen=True)
class MeshProtocolConfig:
    latency_ms: float = 100.0
    jitter_ms: float = 25.0
    handshake_timeout_s: float = 5.0


@dataclass(frozen=True)
class MeshMessage:
    message_id: str
    message_type: MessageType
    source_node: str
    target_node: str
    payload: dict[str, Any]
    sent_at: float
    deliver_at: float

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "payload": self.payload,
            "sent_at": round(self.sent_at, 4),
            "deliver_at": round(self.deliver_at, 4),
            "simulated_latency_ms": round((self.deliver_at - self.sent_at) * 1000, 2),
        }


@dataclass
class ConnectionState:
    local_node: str
    remote_node: str
    status: ConnectionStatus = ConnectionStatus.CLOSED
    last_updated: float = field(default_factory=time.time)


@dataclass(frozen=True)
class QueueUpdatePayload:
    intersection_id: str
    queue_lengths: dict[str, int]
    lane_occupancy: dict[str, float]
    congestion_level: str
    total_vehicles: int
    busiest_approach: str
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "intersection_id": self.intersection_id,
            "queue_lengths": self.queue_lengths,
            "lane_occupancy": self.lane_occupancy,
            "congestion_level": self.congestion_level,
            "total_vehicles": self.total_vehicles,
            "busiest_approach": self.busiest_approach,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueueUpdatePayload:
        return cls(
            intersection_id=data["intersection_id"],
            queue_lengths=dict(data["queue_lengths"]),
            lane_occupancy={key: float(value) for key, value in data["lane_occupancy"].items()},
            congestion_level=data["congestion_level"],
            total_vehicles=int(data["total_vehicles"]),
            busiest_approach=data["busiest_approach"],
            timestamp=float(data["timestamp"]),
        )


@dataclass(frozen=True)
class EmergencyBroadcastPayload:
    source_node: str
    emergency_phase: str
    reason: str
    timestamp: float
    authenticated: bool = True

    def to_dict(self) -> dict:
        return {
            "source_node": self.source_node,
            "emergency_phase": self.emergency_phase,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "authenticated": self.authenticated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmergencyBroadcastPayload:
        return cls(
            source_node=data["source_node"],
            emergency_phase=data["emergency_phase"],
            reason=data["reason"],
            timestamp=float(data["timestamp"]),
            authenticated=bool(data.get("authenticated", True)),
        )


def new_message_id() -> str:
    return uuid.uuid4().hex[:12]


class MeshNetwork:
    """In-memory message bus that simulates delayed delivery between mesh nodes."""

    def __init__(self, config: MeshProtocolConfig | None = None) -> None:
        self.config = config or MeshProtocolConfig()
        self._pending: list[MeshMessage] = []
        self._delivered: list[MeshMessage] = []
        self._inboxes: dict[str, list[MeshMessage]] = {}
        self._clock = time.time()

    @property
    def clock(self) -> float:
        return self._clock

    def advance(self, delta_s: float) -> None:
        if delta_s <= 0:
            raise ValueError("delta_s must be > 0")
        self._clock += delta_s
        self._deliver_due_messages()

    def step(self, delta_s: float | None = None) -> int:
        """Advance simulated time and deliver messages due within that window."""
        if delta_s is None:
            delta_s = max(self.config.latency_ms / 1000.0, 0.001)
        self._clock += delta_s
        return self._deliver_due_messages()

    def flush(self) -> int:
        """Deliver all messages whose delivery time has been reached."""
        return self._deliver_due_messages()

    def _deliver_due_messages(self) -> int:
        ready = [message for message in self._pending if message.deliver_at <= self._clock]
        self._pending = [message for message in self._pending if message.deliver_at > self._clock]

        for message in sorted(ready, key=lambda item: item.deliver_at):
            self._inboxes.setdefault(message.target_node, []).append(message)
            self._delivered.append(message)

        return len(ready)

    def send(self, message: MeshMessage) -> None:
        self._pending.append(message)

    def create_message(
        self,
        message_type: MessageType,
        source_node: str,
        target_node: str,
        payload: dict[str, Any] | None = None,
        *,
        latency_ms: float | None = None,
    ) -> MeshMessage:
        latency = self._latency_seconds(latency_ms)
        sent_at = self._clock
        return MeshMessage(
            message_id=new_message_id(),
            message_type=message_type,
            source_node=source_node,
            target_node=target_node,
            payload=payload or {},
            sent_at=sent_at,
            deliver_at=sent_at + latency,
        )

    def poll_inbox(self, node_id: str) -> list[MeshMessage]:
        messages = self._inboxes.get(node_id, [])
        self._inboxes[node_id] = []
        return messages

    def peek_pending_count(self) -> int:
        return len(self._pending)

    def delivery_log(self) -> tuple[MeshMessage, ...]:
        return tuple(self._delivered)

    def _latency_seconds(self, override_ms: float | None = None) -> float:
        base_ms = self.config.latency_ms if override_ms is None else override_ms
        jitter = self.config.jitter_ms
        if jitter <= 0:
            return base_ms / 1000.0

        # Deterministic pseudo-jitter from clock for repeatable simulation.
        fraction = (self._clock * 1000) % jitter
        return (base_ms + fraction) / 1000.0
