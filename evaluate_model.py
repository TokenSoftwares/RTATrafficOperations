import argparse
import csv
import json
import shutil
from pathlib import Path

from ultralytics import YOLO


DEFAULT_MODEL = "models/best.pt"
DEFAULT_DATA = "data/yolo_sws405/data.yaml"
DEFAULT_OUT = "paper_artifacts/baseline"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate a YOLO model and export paper-ready metrics."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Path to YOLO model weights.")
    parser.add_argument("--data", default=DEFAULT_DATA, help="Path to YOLO data YAML.")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"], help="Dataset split to evaluate.")
    parser.add_argument("--imgsz", type=int, default=640, help="Validation image size.")
    parser.add_argument("--conf", type=float, default=0.001, help="Validation confidence threshold for PR metrics.")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU threshold.")
    parser.add_argument("--batch", type=int, default=4, help="Validation batch size.")
    parser.add_argument("--device", default="cpu", help="Validation device. Use cpu for reproducibility here.")
    parser.add_argument("--name", default="baseline_models_best_test", help="Run name for saved validation plots.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Folder for exported paper artifacts.")
    return parser.parse_args()


def ensure_path(path, label):
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    return path


def metric_value(metrics, name):
    value = getattr(metrics.box, name, None)
    if value is None:
        return None
    try:
        return float(value)
    except TypeError:
        return value


def precision_recall(metrics):
    results = metrics.results_dict
    precision = results.get("metrics/precision(B)")
    recall = results.get("metrics/recall(B)")
    return float(precision), float(recall)


def per_class_rows(metrics, names):
    maps_value = getattr(metrics.box, "maps", [])
    maps = list(maps_value.tolist() if hasattr(maps_value, "tolist") else maps_value)
    rows = []
    for class_id, class_name in names.items():
        class_map = float(maps[class_id]) if class_id < len(maps) else ""
        rows.append(
            {
                "class_id": class_id,
                "class_name": class_name,
                "map50_95": class_map,
            }
        )
    return rows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_raw_confusion_matrix(path, confusion_matrix, names):
    matrix = getattr(confusion_matrix, "matrix", None)
    if matrix is None:
        return False

    matrix_rows = matrix.tolist() if hasattr(matrix, "tolist") else matrix
    labels = [names[index] for index in sorted(names)] + ["background"]
    rows = []
    for row_label, values in zip(labels, matrix_rows):
        row = {"predicted_or_actual": row_label}
        for column_label, value in zip(labels, values):
            row[column_label] = value
        rows.append(row)

    write_csv(path, rows, ["predicted_or_actual", *labels])
    return True


def copy_generated_plots(save_dir, out_dir):
    copied = []
    for pattern in ("*.png", "*.jpg", "*.jpeg"):
        for source in save_dir.glob(pattern):
            destination = out_dir / source.name
            shutil.copy2(source, destination)
            copied.append(destination.as_posix())
    return copied


def main():
    args = parse_args()
    model_path = ensure_path(args.model, "Model")
    data_path = ensure_path(args.data, "Data YAML")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir = out_dir.resolve()

    model = YOLO(str(model_path))
    metrics = model.val(
        data=str(data_path),
        split=args.split,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        batch=args.batch,
        device=args.device,
        plots=True,
        project=str((out_dir / "ultralytics_val_runs").resolve()),
        name=args.name,
        exist_ok=True,
        verbose=True,
    )

    precision, recall = precision_recall(metrics)
    summary = {
        "run_name": args.name,
        "model": model_path.as_posix(),
        "data": data_path.as_posix(),
        "split": args.split,
        "device": args.device,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "conf": args.conf,
        "iou": args.iou,
        "precision": precision,
        "recall": recall,
        "map50": metric_value(metrics, "map50"),
        "map50_95": metric_value(metrics, "map"),
        "map75": metric_value(metrics, "map75"),
        "save_dir": str(metrics.save_dir),
    }

    (out_dir / "baseline_metrics.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    write_csv(out_dir / "baseline_metrics.csv", [summary], list(summary.keys()))

    names = {int(key): value for key, value in model.names.items()}
    class_rows = per_class_rows(metrics, names)
    write_csv(out_dir / "baseline_per_class_map.csv", class_rows, ["class_id", "class_name", "map50_95"])

    try:
        summary_rows = metrics.summary()
        if summary_rows:
            write_csv(out_dir / "baseline_ultralytics_summary.csv", summary_rows, list(summary_rows[0].keys()))
            (out_dir / "baseline_ultralytics_summary.json").write_text(
                json.dumps(summary_rows, indent=2, default=str),
                encoding="utf-8",
            )
            note_path = out_dir / "baseline_summary_note.txt"
            if note_path.exists():
                note_path.unlink()
    except Exception as exc:
        (out_dir / "baseline_summary_note.txt").write_text(
            f"Ultralytics summary export failed: {exc}\n",
            encoding="utf-8",
        )

    if getattr(metrics, "confusion_matrix", None) is not None:
        if write_raw_confusion_matrix(out_dir / "baseline_confusion_matrix.csv", metrics.confusion_matrix, names):
            note_path = out_dir / "baseline_confusion_matrix_note.txt"
            if note_path.exists():
                note_path.unlink()
        else:
            (out_dir / "baseline_confusion_matrix_note.txt").write_text(
                "Confusion matrix image was generated by Ultralytics, but raw matrix export was unavailable.\n",
                encoding="utf-8",
            )

    paper_summary = f"""# Baseline Evaluation Summary

Run: `{args.name}`

Model: `{model_path.as_posix()}`

Dataset: `{data_path.as_posix()}`

Split: `{args.split}`

Device: `{args.device}`

Image size: `{args.imgsz}`

Confidence threshold for validation metrics: `{args.conf}`

NMS IoU threshold: `{args.iou}`

## Overall Metrics

| Metric | Value |
| --- | ---: |
| Precision | {precision:.4f} |
| Recall | {recall:.4f} |
| mAP@0.5 | {summary['map50']:.4f} |
| mAP@0.5:0.95 | {summary['map50_95']:.4f} |
| mAP@0.75 | {summary['map75']:.4f} |

## Per-Class mAP@0.5:0.95

| Class | mAP@0.5:0.95 |
| --- | ---: |
"""
    for row in class_rows:
        paper_summary += f"| {row['class_name']} | {float(row['map50_95']):.4f} |\n"
    paper_summary += "\n## Paper Notes\n\n"
    paper_summary += "- These are the official baseline metrics for comparison against Part 2 improvement experiments.\n"
    paper_summary += "- The evaluation used the existing test split only; no new images or manual annotations were added.\n"
    paper_summary += "- Confusion matrix and PR/F1/P/R curves are saved in this same folder.\n"
    (out_dir / "baseline_paper_summary.md").write_text(paper_summary, encoding="utf-8")

    copied = copy_generated_plots(Path(metrics.save_dir), out_dir)
    (out_dir / "generated_files.json").write_text(
        json.dumps({"copied_plots": copied}, indent=2),
        encoding="utf-8",
    )

    print("Baseline evaluation exported:")
    print(f"  {out_dir / 'baseline_metrics.json'}")
    print(f"  {out_dir / 'baseline_metrics.csv'}")
    print(f"  {out_dir / 'baseline_per_class_map.csv'}")
    print(f"  Ultralytics run: {metrics.save_dir}")


if __name__ == "__main__":
    main()
