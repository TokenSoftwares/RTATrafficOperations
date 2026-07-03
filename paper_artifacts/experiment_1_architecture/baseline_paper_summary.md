# Baseline Evaluation Summary

Run: `exp1_arch_yolov8s_cpu_test`

Model: `runs/detect/runs/detect/exp1_arch_yolov8s_cpu/weights/best.pt`

Dataset: `data/yolo_sws405/data.absolute.yaml`

Split: `test`

Device: `cpu`

Image size: `640`

Confidence threshold for validation metrics: `0.001`

NMS IoU threshold: `0.7`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Precision | 0.6886 |
| Recall | 0.7122 |
| mAP@0.5 | 0.7461 |
| mAP@0.5:0.95 | 0.6054 |
| mAP@0.75 | 0.6657 |

## Per-Class mAP@0.5:0.95

| Class | mAP@0.5:0.95 |
| --- | ---: |
| cctv_camera | 0.7041 |
| desktop_pc | 0.2376 |
| router | 0.7062 |
| smart_board | 0.7740 |

## Paper Notes

- These are the official baseline metrics for comparison against Part 2 improvement experiments.
- The evaluation used the existing test split only; no new images or manual annotations were added.
- Confusion matrix and PR/F1/P/R curves are saved in this same folder.
