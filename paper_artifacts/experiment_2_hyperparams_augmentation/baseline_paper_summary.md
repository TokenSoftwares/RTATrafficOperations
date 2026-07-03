# Baseline Evaluation Summary

Run: `exp2_hyperparams_aug_yolov8s_cpu_test`

Model: `runs/detect/exp2_hyperparams_aug_yolov8s_cpu/weights/best.pt`

Dataset: `data/yolo_sws405/data.absolute.yaml`

Split: `test`

Device: `cpu`

Image size: `640`

Confidence threshold for validation metrics: `0.001`

NMS IoU threshold: `0.7`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Precision | 0.7059 |
| Recall | 0.7246 |
| mAP@0.5 | 0.7568 |
| mAP@0.5:0.95 | 0.5924 |
| mAP@0.75 | 0.6448 |

## Per-Class mAP@0.5:0.95

| Class | mAP@0.5:0.95 |
| --- | ---: |
| cctv_camera | 0.7295 |
| desktop_pc | 0.2938 |
| router | 0.6674 |
| smart_board | 0.6790 |

## Paper Notes

- These are the official baseline metrics for comparison against Part 2 improvement experiments.
- The evaluation used the existing test split only; no new images or manual annotations were added.
- Confusion matrix and PR/F1/P/R curves are saved in this same folder.
