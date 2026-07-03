import argparse
import csv
import random
import shutil
from pathlib import Path

from PIL import Image, ImageOps
from ultralytics import YOLO


CLASS_NAMES = ["cctv_camera", "desktop_pc", "router", "smart_board"]
CLASS_FOLDER_ALIASES = {
    "cctv_cameras": "cctv_camera",
    "desktop_pcs": "desktop_pc",
    "routers": "router",
    "smart_boards": "smart_board",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a YOLO dataset automatically from data/raw/<class_folder> images."
    )
    parser.add_argument("--raw", default="data/raw", help="Raw image folder containing class subfolders.")
    parser.add_argument("--out", default="data/yolo_sws405", help="Output YOLO dataset folder.")
    parser.add_argument("--train", type=float, default=0.8, help="Train split ratio.")
    parser.add_argument("--val", type=float, default=0.1, help="Validation split ratio.")
    parser.add_argument("--seed", type=int, default=405, help="Random split seed.")
    parser.add_argument(
        "--box-size",
        type=float,
        default=0.9,
        help="Weak-label box size from 0 to 1. 0.9 means one centered box covering 90%% of the image.",
    )
    parser.add_argument(
        "--pseudo-model",
        default="models/best.pt",
        help="Use this model to auto-create tighter labels when it detects the expected class. Use 'none' to disable.",
    )
    parser.add_argument(
        "--pseudo-conf",
        type=float,
        default=0.15,
        help="Minimum confidence for accepting a pseudo-label from --pseudo-model.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the output dataset folder before rebuilding.",
    )
    return parser.parse_args()


def find_images(raw_dir):
    items = []
    for folder in sorted(raw_dir.iterdir()):
        if not folder.is_dir():
            continue

        class_name = CLASS_FOLDER_ALIASES.get(folder.name, folder.name)
        if class_name not in CLASS_NAMES:
            print(f"Skipping unknown class folder: {folder}")
            continue

        class_id = CLASS_NAMES.index(class_name)
        for image_path in sorted(folder.rglob("*")):
            if image_path.suffix.lower() in IMAGE_EXTENSIONS:
                items.append((image_path, class_id, class_name))
    return items


def split_items(items, train_ratio, val_ratio, seed):
    random.Random(seed).shuffle(items)

    train_end = int(len(items) * train_ratio)
    val_end = train_end + int(len(items) * val_ratio)

    return {
        "train": items[:train_end],
        "val": items[train_end:val_end],
        "test": items[val_end:],
    }


def safe_stem(path, class_name, index):
    stem = "".join(char if char.isalnum() or char in "-_" else "_" for char in path.stem)
    return f"{class_name}_{index:05d}_{stem}"


def save_image(source, destination):
    try:
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.save(destination, quality=95)
            return True
    except Exception as exc:
        print(f"Skipping unreadable image: {source} ({exc})")
        return False


def centered_label(class_id, box_size):
    box_size = max(0.05, min(box_size, 1.0))
    return class_id, 0.5, 0.5, box_size, box_size, "center_fallback", 0.0


def pseudo_label(model, source, class_id, pseudo_conf, box_size):
    if model is None:
        return centered_label(class_id, box_size)

    result = model.predict(source=str(source), conf=pseudo_conf, verbose=False)[0]
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return centered_label(class_id, box_size)

    image_height, image_width = result.orig_shape
    best_box = None
    best_confidence = -1.0

    for box in boxes:
        detected_class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        if detected_class_id == class_id and confidence > best_confidence:
            best_box = box
            best_confidence = confidence

    if best_box is None:
        return centered_label(class_id, box_size)

    x1, y1, x2, y2 = best_box.xyxy[0].tolist()
    x_center = ((x1 + x2) / 2) / image_width
    y_center = ((y1 + y2) / 2) / image_height
    width = (x2 - x1) / image_width
    height = (y2 - y1) / image_height

    values = [max(0.0, min(value, 1.0)) for value in (x_center, y_center, width, height)]
    return class_id, *values, "model_pseudo", best_confidence


def write_label(label_path, label):
    class_id, x_center, y_center, width, height, _, _ = label
    label_path.write_text(
        f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n",
        encoding="utf-8",
    )


def write_data_yaml(out_dir):
    names = "\n".join(f"  {index}: {name}" for index, name in enumerate(CLASS_NAMES))
    content = f"""path: {out_dir.as_posix()}
train: images/train
val: images/val
test: images/test

names:
{names}
"""
    (out_dir / "data.yaml").write_text(content, encoding="utf-8")


def load_pseudo_model(model_path):
    if not model_path or model_path.lower() == "none":
        return None

    path = Path(model_path)
    if not path.exists():
        print(f"Pseudo-label model not found, using centered fallback only: {path}")
        return None

    print(f"Loading pseudo-label model: {path}")
    return YOLO(str(path))


def build_dataset(args):
    raw_dir = Path(args.raw)
    out_dir = Path(args.out)

    if not raw_dir.exists():
        raise SystemExit(f"Raw folder not found: {raw_dir}")

    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)

    items = find_images(raw_dir)
    if not items:
        raise SystemExit(f"No images found in: {raw_dir}")

    splits = split_items(items, args.train, args.val, args.seed)
    pseudo_model = load_pseudo_model(args.pseudo_model)
    counts = {class_name: 0 for class_name in CLASS_NAMES}
    label_source_counts = {"model_pseudo": 0, "center_fallback": 0}
    split_counts = {}
    label_report_rows = []

    for split, split_items_list in splits.items():
        image_dir = out_dir / "images" / split
        label_dir = out_dir / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        split_counts[split] = 0

        for index, (source, class_id, class_name) in enumerate(split_items_list, start=1):
            name = safe_stem(source, class_name, index)
            image_destination = image_dir / f"{name}.jpg"
            label_destination = label_dir / f"{name}.txt"

            if not save_image(source, image_destination):
                continue

            label = pseudo_label(pseudo_model, source, class_id, args.pseudo_conf, args.box_size)
            write_label(label_destination, label)

            _, x_center, y_center, width, height, label_source, confidence = label
            label_source_counts[label_source] += 1
            label_report_rows.append(
                {
                    "split": split,
                    "class": class_name,
                    "image": str(image_destination),
                    "label_source": label_source,
                    "confidence": f"{confidence:.4f}",
                    "x_center": f"{x_center:.6f}",
                    "y_center": f"{y_center:.6f}",
                    "width": f"{width:.6f}",
                    "height": f"{height:.6f}",
                    "source": str(source),
                }
            )
            counts[class_name] += 1
            split_counts[split] += 1

    write_data_yaml(out_dir)
    with (out_dir / "label_report.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(label_report_rows[0].keys()))
        writer.writeheader()
        writer.writerows(label_report_rows)

    print(f"Built YOLO dataset: {out_dir}")
    print(f"Data config: {out_dir / 'data.yaml'}")
    print("\nSplit counts:")
    for split, count in split_counts.items():
        print(f"  {split}: {count}")

    print("\nClass counts:")
    for class_name, count in counts.items():
        print(f"  {class_name}: {count}")

    print("\nLabel sources:")
    for source, count in label_source_counts.items():
        print(f"  {source}: {count}")

    print("\nImportant: labels are still automatic. Model pseudo-labels are better than centered boxes,")
    print("but any center_fallback labels are weak and less accurate than real manual boxes.")


def main():
    build_dataset(parse_args())


if __name__ == "__main__":
    main()
