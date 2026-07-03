"""Vehicle detection service backed by a pretrained Ultralytics YOLO model.

All YOLO-specific logic lives in this module. Other project code should import
``Detector`` and ``Vehicle`` only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Union

from ultralytics import YOLO


# COCO class names accepted as road vehicles for the traffic capstone prototype.
VEHICLE_CLASS_NAMES = frozenset({"car", "motorcycle", "bus", "truck"})

SourcePath = Union[str, Path]


@dataclass(frozen=True)
class Vehicle:
    """Structured detection returned by :class:`Detector`."""

    id: int
    type: str
    confidence: float
    bbox: tuple[float, float, float, float]
    center: tuple[float, float]
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "confidence": round(self.confidence, 4),
            "bbox": [round(v, 1) for v in self.bbox],
            "center": [round(v, 1) for v in self.center],
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class DetectionResult:
    """Output of a single detection pass."""

    vehicles: tuple[Vehicle, ...]
    source: str
    model_name: str
    inference_ms: float
    image_width: int
    image_height: int
    annotated_image_path: str | None = None

    @property
    def vehicle_count(self) -> int:
        return len(self.vehicles)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "model_name": self.model_name,
            "inference_ms": round(self.inference_ms, 2),
            "image_width": self.image_width,
            "image_height": self.image_height,
            "vehicle_count": self.vehicle_count,
            "vehicles": [vehicle.to_dict() for vehicle in self.vehicles],
            "annotated_image_path": self.annotated_image_path,
        }


class Detector:
    """Reusable vehicle detection service for demos, simulators, and edge nodes."""

    DEFAULT_MODEL = "yolov8n.pt"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        confidence: float = 0.25,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.confidence = confidence
        self.device = device
        self._model: YOLO | None = None
        self._vehicle_class_ids: set[int] | None = None

    def load(self) -> None:
        """Load the YOLO model if it is not already loaded."""
        if self._model is None:
            self._model = YOLO(self.model_name)
            self._vehicle_class_ids = {
                class_id
                for class_id, name in self._model.names.items()
                if name in VEHICLE_CLASS_NAMES
            }

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def detect(
        self,
        source: SourcePath,
        *,
        save_annotated_to: SourcePath | None = None,
    ) -> DetectionResult:
        """Run vehicle detection on an image path and return structured results."""
        self.load()
        assert self._model is not None
        assert self._vehicle_class_ids is not None

        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Image not found: {source_path}")

        started = time.perf_counter()
        results = self._model.predict(
            source=str(source_path),
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )
        inference_ms = (time.perf_counter() - started) * 1000

        result = results[0]
        image_height, image_width = result.orig_shape
        timestamp = time.time()
        vehicles = self._parse_vehicles(result, timestamp)

        annotated_path: str | None = None
        if save_annotated_to is not None:
            output_path = Path(save_annotated_to)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result.save(filename=str(output_path))
            annotated_path = str(output_path.resolve())

        return DetectionResult(
            vehicles=tuple(vehicles),
            source=str(source_path.resolve()),
            model_name=self.model_name,
            inference_ms=inference_ms,
            image_width=image_width,
            image_height=image_height,
            annotated_image_path=annotated_path,
        )

    def detect_many(
        self,
        sources: Sequence[SourcePath],
        *,
        save_annotated_dir: SourcePath | None = None,
    ) -> list[DetectionResult]:
        """Run detection on multiple image paths."""
        outputs: list[DetectionResult] = []
        for index, source in enumerate(sources):
            annotated_target = None
            if save_annotated_dir is not None:
                source_path = Path(source)
                annotated_target = Path(save_annotated_dir) / f"{source_path.stem}_{index:03d}.jpg"
            outputs.append(
                self.detect(source, save_annotated_to=annotated_target),
            )
        return outputs

    def _parse_vehicles(self, result, timestamp: float) -> list[Vehicle]:
        assert self._vehicle_class_ids is not None

        vehicles: list[Vehicle] = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return vehicles

        for vehicle_id, box in enumerate(boxes):
            class_id = int(box.cls[0])
            if class_id not in self._vehicle_class_ids:
                continue

            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            vehicles.append(
                Vehicle(
                    id=vehicle_id,
                    type=result.names[class_id],
                    confidence=float(box.conf[0]),
                    bbox=(x1, y1, x2, y2),
                    center=((x1 + x2) / 2, (y1 + y2) / 2),
                    timestamp=timestamp,
                )
            )
        return vehicles
