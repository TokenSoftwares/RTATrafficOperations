# Experiment 2 Plan: Hyperparameter and Augmentation Optimization

## Status Before Experiment 2

Baseline test metrics:

| Metric | Baseline |
| --- | ---: |
| Precision | 0.7801 |
| Recall | 0.5529 |
| mAP@0.5 | 0.5145 |
| mAP@0.5:0.95 | 0.4939 |

Experiment 1 test metrics:

| Metric | Experiment 1 |
| --- | ---: |
| Precision | 0.6886 |
| Recall | 0.7122 |
| mAP@0.5 | 0.7461 |
| mAP@0.5:0.95 | 0.6054 |

Experiment 1 passed because recall, mAP@0.5, and mAP@0.5:0.95 improved over baseline. The main drawback is that precision decreased, and `desktop_pc` performance regressed.

## Purpose

Experiment 2 will test whether hyperparameter and automated augmentation changes can improve generalization while keeping the dataset fixed.

This experiment satisfies:

- Category A: Hyperparameter optimization.
- Category B: Automated data augmentation.

No new images will be added. No manual annotation will be performed.

## Research Question

Can training-time hyperparameter and augmentation changes improve recall and mAP while reducing the precision tradeoff observed in Experiment 1?

## Recommended Setup

Use the Experiment 1 architecture (`YOLOv8s`) because it already improved overall performance.

Suggested training source:

```text
yolov8s.pt
```

Dataset:

```text
data/yolo_sws405/data.absolute.yaml
```

Device:

```text
cpu
```

## Proposed Training Settings

| Setting | Value |
| --- | --- |
| Model | `yolov8s.pt` |
| Epochs | `15` |
| Batch | `4` |
| Image size | `640` |
| Device | `cpu` |
| Seed | `405` |
| Patience | `5` |
| Cosine LR | `True` |
| Weight decay | `0.0007` |
| HSV hue | `0.015` |
| HSV saturation | `0.7` |
| HSV brightness | `0.4` |
| Translate | `0.1` |
| Scale | `0.5` |
| Horizontal flip | `0.5` |
| Mosaic | `1.0` |
| MixUp | `0.0` initially |

Do not enable aggressive rotation or vertical flipping because routers, smart boards, and desktop PCs have natural orientations.

## Expected Benefit

- Improve robustness to lighting changes.
- Improve object-scale variation.
- Improve recall without relying on new images.
- Possibly recover some precision lost in Experiment 1.

## Success Criteria

Experiment 2 passes if it improves at least one of the following compared with Experiment 1:

- Precision, preferably above `0.6886`.
- mAP@0.5, preferably above `0.7461`.
- mAP@0.5:0.95, preferably above `0.6054`.
- `desktop_pc` mAP@0.5:0.95, preferably above `0.2376`.

If Experiment 2 improves precision but slightly lowers recall, it may still be useful as a tradeoff experiment in the paper.

## Required Outputs

Save outputs to:

```text
paper_artifacts/experiment_2_hyperparams_augmentation/
```

Required files:

- Training config JSON.
- Training `args.yaml`.
- Training `results.csv`.
- Training `results.png`.
- Test evaluation metrics CSV/JSON.
- Per-class summary CSV.
- Confusion matrix PNG.
- Normalized confusion matrix PNG.
- PR/F1/P/R curves.
- Paper summary Markdown.

## Paper Interpretation Template

If Experiment 2 improves results:

> The hyperparameter and augmentation experiment improved generalization without adding images or manual annotations. This suggests that training-time transformations can partially compensate for limited dataset diversity.

If Experiment 2 fails:

> The hyperparameter and augmentation experiment did not outperform the architecture-only model. This suggests that the remaining errors are more strongly related to label quality and class-specific ambiguity than to insufficient augmentation.

## Next Step

Create a dedicated training script:

```text
train_experiment_hyperparams.py
```

Then run training and evaluate the resulting `best.pt` on the same test split.
