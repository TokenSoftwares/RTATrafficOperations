import argparse
import json
import shutil
from pathlib import Path

from ultralytics import YOLO


DEFAULT_MODEL = "yolov8s.pt"
DEFAULT_DATA = "data/yolo_sws405/data.yaml"
DEFAULT_PROJECT = "runs/detect"
DEFAULT_NAME = "exp2_hyperparams_aug_yolov8s_cpu"
DEFAULT_ARTIFACT_DIR = "paper_artifacts/experiment_2_hyperparams_augmentation"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train Experiment 2: YOLO hyperparameter and augmentation optimization."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Pretrained YOLO model to fine-tune.")
    parser.add_argument("--data", default=DEFAULT_DATA, help="YOLO dataset YAML.")
    parser.add_argument("--epochs", type=int, default=15, help="Training epochs. CPU-friendly default.")
    parser.add_argument("--batch", type=int, default=4, help="Training batch size.")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size.")
    parser.add_argument("--device", default="cpu", help="Training device. Default is CPU.")
    parser.add_argument("--seed", type=int, default=405, help="Random seed for reproducibility.")
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Ultralytics project directory.")
    parser.add_argument("--name", default=DEFAULT_NAME, help="Ultralytics run name.")
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR, help="Paper artifact export folder.")
    parser.add_argument("--exist-ok", action="store_true", help="Allow overwriting an existing run folder.")
    return parser.parse_args()


def ensure_data(path):
    data_path = Path(path)
    if not data_path.exists():
        raise SystemExit(f"Dataset YAML not found: {data_path}")
    return data_path


def copy_if_exists(source, destination_dir):
    source = Path(source)
    if source.exists():
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination_dir / source.name)


def main():
    args = parse_args()
    data_path = ensure_data(args.data)
    project_dir = Path(args.project).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "experiment": "Experiment 2: Hyperparameter and Augmentation Optimization",
        "strategy_category": "Category A - Hyperparameter Optimization; Category B - Automated Data Augmentation",
        "strategy": "Tune training hyperparameters and augmentation while keeping the existing dataset fixed.",
        "model": args.model,
        "data": data_path.as_posix(),
        "epochs": args.epochs,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "device": args.device,
        "seed": args.seed,
        "patience": args.patience,
        "project": project_dir.as_posix(),
        "name": args.name,
        "cos_lr": True,
        "weight_decay": 0.0007,
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
        "translate": 0.1,
        "scale": 0.5,
        "fliplr": 0.5,
        "flipud": 0.0,
        "degrees": 0.0,
        "mosaic": 1.0,
        "mixup": 0.0,
        "new_images_added": False,
        "manual_annotation_performed": False,
    }
    (artifact_dir / "experiment_2_config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    model = YOLO(args.model)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        seed=args.seed,
        deterministic=True,
        patience=args.patience,
        pretrained=True,
        project=str(project_dir),
        name=args.name,
        exist_ok=args.exist_ok,
        plots=True,
        val=True,
        cos_lr=True,
        weight_decay=0.0007,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        flipud=0.0,
        degrees=0.0,
        mosaic=1.0,
        mixup=0.0,
    )

    save_dir = Path(results.save_dir)
    (artifact_dir / "experiment_2_train_result.json").write_text(
        json.dumps({"save_dir": save_dir.as_posix()}, indent=2),
        encoding="utf-8",
    )

    copy_if_exists(save_dir / "args.yaml", artifact_dir)
    copy_if_exists(save_dir / "results.csv", artifact_dir)
    copy_if_exists(save_dir / "results.png", artifact_dir)

    weights_dir = save_dir / "weights"
    if weights_dir.exists():
        (artifact_dir / "weights_location.txt").write_text(
            f"Best weights: {(weights_dir / 'best.pt').as_posix()}\nLast weights: {(weights_dir / 'last.pt').as_posix()}\n",
            encoding="utf-8",
        )

    print("Experiment 2 training complete.")
    print(f"Run directory: {save_dir}")
    print(f"Paper artifacts: {artifact_dir}")
    print("Next: evaluate best.pt with evaluate_model.py and update experiment_log.csv.")


if __name__ == "__main__":
    main()
