# Experiment 2 Evaluation Summary

Run: `exp2_hyperparams_aug_yolov8s_cpu_test`

Strategy: Category A - Hyperparameter Optimization; Category B - Automated Data Augmentation

Model: `runs/detect/exp2_hyperparams_aug_yolov8s_cpu/weights/best.pt`

Dataset: `data/yolo_sws405/data.absolute.yaml`

Split: `test`

Device: `cpu`

Image size: `640`

Confidence threshold for validation metrics: `0.001`

NMS IoU threshold: `0.7`

## Overall Metrics

| Metric | Baseline | Experiment 1 | Experiment 2 |
| --- | ---: | ---: | ---: |
| Precision | 0.7801 | 0.6886 | 0.7059 |
| Recall | 0.5529 | 0.7122 | 0.7246 |
| mAP@0.5 | 0.5145 | 0.7461 | 0.7568 |
| mAP@0.5:0.95 | 0.4939 | 0.6054 | 0.5924 |

## Change Against Experiment 1

| Metric | Change |
| --- | ---: |
| Precision | +0.0173 |
| Recall | +0.0124 |
| mAP@0.5 | +0.0107 |
| mAP@0.5:0.95 | -0.0130 |

## Per-Class Results

| Class | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
| --- | ---: | ---: | ---: | ---: |
| cctv_camera | 0.8586 | 0.9000 | 0.9358 | 0.7295 |
| desktop_pc | 0.5782 | 0.4348 | 0.4671 | 0.2938 |
| router | 0.8677 | 0.7857 | 0.7942 | 0.6674 |
| smart_board | 0.5191 | 0.7778 | 0.8300 | 0.6790 |

## Interpretation For Paper

- Experiment 2 passes as a controlled second improvement strategy because it improves precision, recall, and mAP@0.5 compared with Experiment 1.
- Experiment 2 also improves `desktop_pc` performance compared with Experiment 1, addressing the main class-specific regression from the architecture upgrade.
- mAP@0.5:0.95 decreases slightly compared with Experiment 1, so Experiment 1 remains stronger for stricter localization quality.
- The result shows a tradeoff: augmentation and training hyperparameter changes improve detection coverage and desktop PC recovery but slightly reduce strict box-quality performance.
- No new images or manual annotations were used.

## Paper Artifacts

- Confusion matrix: `confusion_matrix.png`
- Normalized confusion matrix: `confusion_matrix_normalized.png`
- PR curve: `BoxPR_curve.png`
- F1 curve: `BoxF1_curve.png`
- Training curve: `results.png`
- Training metrics: `results.csv`
- Evaluation metrics: `baseline_metrics.csv` and `baseline_ultralytics_summary.csv`
