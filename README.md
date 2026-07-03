# AI Edge Mesh Traffic Control — Capstone Demo

End-to-end simulation of an AI-powered edge mesh traffic control system for a three-intersection Dubai corridor (J1 → J2 → J3). Built for BUS310 presentation.

The system wires vehicle detection, queue estimation, signal optimization, safety validation, mesh communication, and a live RTA-style operations dashboard.

## Quick Start

```bash
cd code
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 run_demo.py
```

Open **http://127.0.0.1:5002**

On first run, Ultralytics may download `yolov8n.pt` automatically (~6 MB).

## What You Get

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:5002 | **Main capstone dashboard** — scenarios, map, stats, event log, CCTV modal |
| http://127.0.0.1:5001 | Milestone 1 vehicle detection upload demo (`live_traffic_demo_web.py`) |

## Demo Scenarios

Switch scenarios from the dashboard during the presentation:

1. **Normal Traffic** — baseline corridor operation
2. **Rush Hour** — higher vehicle counts and congestion
3. **Accident** — J2 receives a rejected unsafe signal decision
4. **Emergency Vehicle** — green corridor animation along J1 → J2 → J3
5. **Heavy Rain** — reduced visibility / lower detection confidence

## Dashboard Features

- **Live statistics bar** — vehicles, queue, congestion, mesh messages, safety approvals, emergency events
- **Live event log** — newest events at the top
- **Live map view** — traffic-light markers, mesh link pulses, emergency corridor animation
- **CCTV modal** — click any intersection card or map marker to open a camera feed with live simulation stats

### CCTV Modal

- Reuses `assets/demo_traffic.mp4` for all three intersections
- Different start timestamps per junction (J1: 0s, J2: 12s, J3: 24s)
- Shows Camera ID, LIVE badge, signal, vehicles, queue, congestion, safety status, and AI recommendation
- Dashboard keeps running in the background while the modal is open

## Architecture

```text
Detector → Vehicle → EdgeNode → Intersection
                        ↓
              QueueEstimator → SignalOptimizer → SignalDecision
                        ↓
                   SafetyKernel → Approved / Rejected
                        ↓
                   TrafficLight (passive actuator)
                        ↓
                   MeshNode → MeshNetwork
                        ↓
                   CentralHub (monitoring only) → Dashboard
```

## Project Layout

```text
code/
  run_demo.py                 # Single entry point for the capstone demo
  live_dashboard_web.py       # RTA operations dashboard (port 5002)
  demo_simulator.py           # End-to-end simulation loop
  demo_scenarios.py           # Five scenario definitions
  central_hub.py              # Monitoring-only central hub
  traffic_detection.py        # YOLO vehicle detection service
  edge_node.py                # Edge node (light + intersection)
  queue_estimator.py          # Queue / congestion estimation
  signal_optimizer.py         # Signal timing decisions
  safety_kernel.py            # Safety validation layer
  mesh_protocol.py            # Mesh message protocol
  mesh_node.py                # Mesh networking layer
  intersections.json          # Map coordinates and corridor topology
  assets/demo_traffic.mp4     # CCTV demo video
  live_traffic_demo_web.py    # Milestone 1 detection demo (port 5001)
```

## Milestone 1 — Vehicle Detection

Run the standalone detection demo:

```bash
python3 live_traffic_demo_web.py
```

Open **http://127.0.0.1:5001**, upload a road/intersection image, and inspect structured `Vehicle` detections (car, motorcycle, bus, truck).

## Requirements

- Python 3.10+ (3.12 recommended)
- CPU is sufficient for the presentation demo
- Dependencies: `ultralytics`, `flask`, `opencv-python`, `pillow`

See `requirements.txt` for the full list.

## Presentation Tips

1. Start with **Normal Traffic** on the dashboard view
2. Switch to **Live Map View** to show mesh pulses and signal states
3. Run **Accident** to show a safety rejection at J2
4. Run **Emergency Vehicle** for the green corridor animation
5. Click **J1 / J2 / J3** (card or map marker) to open the CCTV modal
6. End with **Heavy Rain** to show degraded conditions

---

## Legacy: Smart Campus Device Detection (BCS407)

This repository also contains the original Smart Campus YOLO project (cctv_camera, desktop_pc, router, smart_board).

| Item | Path |
| --- | --- |
| Baseline weights | `models/best.pt` |
| Final model weights | `final_weights/best.pt` |
| Dataset | `data/yolo_sws405/` |
| Experiment artifacts | `paper_artifacts/` |

### Smart Campus demos

```bash
python3 live_demo_web.py          # http://127.0.0.1:5000
python3 live_demo_ui.py           # Desktop UI
python3 evaluate_model.py --help  # Model evaluation
```

Final selected model (Experiment 2): Precision 0.7059, Recall 0.7246, mAP@0.5 0.7568.
