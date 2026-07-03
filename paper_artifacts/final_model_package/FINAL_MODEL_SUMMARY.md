# Final Model Summary

Selected final model: Experiment 2.

Model path:

`runs/detect/exp2_hyperparams_aug_yolov8s_cpu/weights/best.pt`

## Reason For Selection

Experiment 2 was selected as the final balanced model because it achieved the best recall and best mAP@0.5 while improving precision over Experiment 1. Experiment 1 had the best mAP@0.5:0.95, so it remains the strongest strict-localization run, but Experiment 2 is more balanced for a prototype smart campus detector.

## Consolidated Results

| Run | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 0.7801 | 0.5529 | 0.5145 | 0.4939 |
| Experiment 1 | 0.6886 | 0.7122 | 0.7461 | 0.6054 |
| Experiment 2 | 0.7059 | 0.7246 | 0.7568 | 0.5924 |

## Paper Interpretation

- Baseline was conservative, with higher precision but weak recall.
- Experiment 1 improved recall and strict mAP through architecture upgrade.
- Experiment 2 improved balance through hyperparameter optimization and augmentation.
- No new images were added.
- No manual annotation was performed.
- Remaining limitations include pseudo-label quality, fallback labels, and limited real-world campus validation.
