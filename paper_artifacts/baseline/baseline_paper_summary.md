# Baseline Evaluation Summary

Run: `baseline_models_best_test`

Model: `models/best.pt`

Dataset: `data/yolo_sws405/data.absolute.yaml`

Split: `test`

Device: `cpu`

Image size: `640`

Confidence threshold for validation metrics: `0.001`

NMS IoU threshold: `0.7`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Precision | 0.7801 |
| Recall | 0.5529 |
| mAP@0.5 | 0.5145 |
| mAP@0.5:0.95 | 0.4939 |
| mAP@0.75 | 0.5028 |

## Per-Class mAP@0.5:0.95

| Class | mAP@0.5:0.95 |
| --- | ---: |
| cctv_camera | 0.5807 |
| desktop_pc | 0.4618 |
| router | 0.7116 |
| smart_board | 0.2215 |

## Paper Notes

- These are the official baseline metrics for comparison against Part 2 improvement experiments.
- The evaluation used the existing test split only; no new images or manual annotations were added.
- Confusion matrix and PR/F1/P/R curves are saved in this same folder.
