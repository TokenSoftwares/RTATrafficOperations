# Experiment 1 Evaluation Summary

Run: `exp1_arch_yolov8s_cpu_test`

Strategy: Category A - Model/Architecture Upgrade

Model: `runs/detect/runs/detect/exp1_arch_yolov8s_cpu/weights/best.pt`

Dataset: `data/yolo_sws405/data.absolute.yaml`

Split: `test`

Device: `cpu`

Image size: `640`

Confidence threshold for validation metrics: `0.001`

NMS IoU threshold: `0.7`

## Overall Metrics

| Metric | Baseline | Experiment 1 | Change |
| --- | ---: | ---: | ---: |
| Precision | 0.7801 | 0.6886 | -0.0915 |
| Recall | 0.5529 | 0.7122 | +0.1593 |
| mAP@0.5 | 0.5145 | 0.7461 | +0.2316 |
| mAP@0.5:0.95 | 0.4939 | 0.6054 | +0.1115 |

## Per-Class Results

| Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
| --- | ---: | ---: | ---: | ---: |
| cctv_camera | 0.7873 | 0.9000 | 0.9107 | 0.7041 |
| desktop_pc | 0.4379 | 0.3478 | 0.3381 | 0.2376 |
| router | 0.8195 | 0.7857 | 0.8523 | 0.7062 |
| smart_board | 0.7096 | 0.8153 | 0.8834 | 0.7740 |

## Interpretation For Paper

- Experiment 1 passes because it improves recall, mAP@0.5, and mAP@0.5:0.95 over the baseline.
- The architecture upgrade substantially improves `smart_board`, the weakest baseline class.
- Precision decreases from 0.7801 to 0.6886, meaning the improved model is less conservative and introduces more false positives.
- The tradeoff is acceptable because recall and mAP improve strongly, which directly addresses the baseline weakness of missed detections.
- `desktop_pc` performance decreases and should be discussed as a class-specific regression.
- No new images or manual annotations were used.

## Paper Artifacts

- Confusion matrix: `confusion_matrix.png`
- Normalized confusion matrix: `confusion_matrix_normalized.png`
- PR curve: `BoxPR_curve.png`
- F1 curve: `BoxF1_curve.png`
- Training curve: `results.png`
- Training metrics: `results.csv`
- Evaluation metrics: `baseline_metrics.csv` and `baseline_ultralytics_summary.csv`
