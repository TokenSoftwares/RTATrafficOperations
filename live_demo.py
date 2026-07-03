import argparse
from pathlib import Path

from ultralytics import YOLO


FINAL_MODEL_PATH = Path("final_weights/best.pt")
DEFAULT_MODEL_PATH = FINAL_MODEL_PATH if FINAL_MODEL_PATH.exists() else Path("models/best.pt")
DEFAULT_OUTPUT_PATH = Path("runs/live_inference_result.jpg")
TEAM_TEXT = "Done by Saleh Dweik - 20230003058, Mohammad Jaafrie - 20220001221, Xavier - 20230003339, Rithik Manohar - 20220002309, and Abir Hossain - 20220001382."


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run live YOLO inference for the SWS405 Smart Campus presentation."
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to an unseen image. If omitted, you will be prompted for one.",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL_PATH),
        help="Path to the trained YOLO model.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.30,
        help="Minimum confidence threshold for displayed detections.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Where to save the annotated image.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Save and print results without opening the display window.",
    )
    return parser.parse_args()


def get_image_path(image_arg):
    image_path = image_arg or input("Enter the instructor's unseen image path: ").strip()
    if not image_path:
        raise SystemExit("No image path provided.")

    path = Path(image_path).expanduser()
    if not path.exists():
        raise SystemExit(f"Image not found: {path}")
    if not path.is_file():
        raise SystemExit(f"Path is not a file: {path}")
    return path


def print_detection_summary(result):
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        print("No objects detected above the confidence threshold.")
        print("Explain: this may be correct if the target devices are absent, or an error if the object is too small, occluded, blurry, or outside the trained classes.")
        return

    print("\nDetections to explain during presentation:")
    print("#  Class Prediction        Confidence  Bounding Box [x1, y1, x2, y2]")
    for index, box in enumerate(boxes, start=1):
        class_id = int(box.cls[0])
        class_name = result.names[class_id]
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = [round(value, 1) for value in box.xyxy[0].tolist()]
        print(f"{index:<2} {class_name:<23} {confidence:.2f}        [{x1}, {y1}, {x2}, {y2}]")


def main():
    args = parse_args()
    image_path = get_image_path(args.image)
    model_path = Path(args.model)
    output_path = Path(args.output)

    if not model_path.exists():
        raise SystemExit(f"Model not found: {model_path}")

    print("Smart Campus Device Detection")
    print(TEAM_TEXT)
    print("Loading Smart Campus model...")
    model = YOLO(str(model_path))

    print(f"Running live inference on unseen image: {image_path}")
    results = model.predict(source=str(image_path), conf=args.conf, verbose=False)
    result = results[0]

    annotated_image = result.plot()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(filename=str(output_path))

    print_detection_summary(result)
    print(f"\nAnnotated image saved to: {output_path}")

    if not args.no_show:
        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "OpenCV is required to display the image window. Install it with: "
                "venv\\Scripts\\python.exe -m pip install opencv-python\n"
                f"The annotated image was still saved to: {output_path}"
            ) from exc

        cv2.imshow("Smart Campus Device Detection - boxes, classes, confidence", annotated_image)
        print("Press any key on the image window to close it.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
