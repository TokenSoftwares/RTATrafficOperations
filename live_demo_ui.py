from pathlib import Path
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from PIL import Image, ImageTk
from ultralytics import YOLO

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ModuleNotFoundError:
    DND_FILES = None
    TkinterDnD = None


FINAL_MODEL_PATH = Path("final_weights/best.pt")
MODEL_PATH = FINAL_MODEL_PATH if FINAL_MODEL_PATH.exists() else Path("models/best.pt")
OUTPUT_PATH = Path("runs/live_inference_result.jpg")
CONFIDENCE = 0.30
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TEAM_TEXT = "Done by Saleh Dweik - 20230003058, Mohammad Jaafrie - 20220001221, Xavier - 20230003339, Rithik Manohar - 20220002309, and Abir Hossain - 20220001382."


class LiveInferenceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SWS405 Smart Campus Live Inference")
        self.root.geometry("1000x720")
        self.root.minsize(820, 600)

        self.model = None
        self.current_image = None
        self.preview_image = None

        self.status_var = tk.StringVar(value="Drop an image here or click Browse.")
        self.path_var = tk.StringVar(value="No image selected")

        self.build_ui()
        self.load_model_async()

    def build_ui(self):
        self.root.configure(bg="#101820")

        title = tk.Label(
            self.root,
            text="Smart Campus Device Detection",
            fg="white",
            bg="#101820",
            font=("Segoe UI", 22, "bold"),
        )
        title.pack(pady=(18, 4))

        subtitle = tk.Label(
            self.root,
            text="Drag and drop an image to show bounding boxes, confidence scores, and class predictions.",
            fg="#c8d3dc",
            bg="#101820",
            font=("Segoe UI", 11),
        )
        subtitle.pack(pady=(0, 14))

        team = tk.Label(
            self.root,
            text=TEAM_TEXT,
            fg="#c8d3dc",
            bg="#101820",
            font=("Segoe UI", 9),
            wraplength=900,
        )
        team.pack(pady=(0, 10))

        content = tk.Frame(self.root, bg="#101820")
        content.pack(fill=tk.BOTH, expand=True, padx=18, pady=10)

        left = tk.Frame(content, bg="#182a36", bd=0, relief=tk.FLAT)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        right = tk.Frame(content, bg="#182a36", width=330)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        self.drop_area = tk.Label(
            left,
            text="Drop image here\n\nor click Browse",
            fg="#dce7ef",
            bg="#243b4a",
            font=("Segoe UI", 18, "bold"),
            relief=tk.RIDGE,
            bd=2,
        )
        self.drop_area.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        if DND_FILES:
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind("<<Drop>>", self.handle_drop)
        else:
            self.drop_area.configure(text="Drag/drop dependency missing\n\nUse Browse or install tkinterdnd2")

        controls = tk.Frame(right, bg="#182a36")
        controls.pack(fill=tk.X, padx=14, pady=(16, 8))

        browse_btn = tk.Button(
            controls,
            text="Browse Image",
            command=self.browse_image,
            bg="#2f80ed",
            fg="white",
            activebackground="#1f6fd1",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=8,
        )
        browse_btn.pack(fill=tk.X)

        self.run_btn = tk.Button(
            controls,
            text="Run Inference",
            command=self.run_inference_async,
            bg="#27ae60",
            fg="white",
            activebackground="#219653",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=8,
            state=tk.DISABLED,
        )
        self.run_btn.pack(fill=tk.X, pady=(10, 0))

        path_label = tk.Label(
            right,
            textvariable=self.path_var,
            fg="#c8d3dc",
            bg="#182a36",
            wraplength=290,
            justify=tk.LEFT,
            font=("Segoe UI", 9),
        )
        path_label.pack(fill=tk.X, padx=14, pady=(6, 10))

        results_label = tk.Label(
            right,
            text="Predictions",
            fg="white",
            bg="#182a36",
            anchor="w",
            font=("Segoe UI", 13, "bold"),
        )
        results_label.pack(fill=tk.X, padx=14, pady=(8, 4))

        self.results_box = scrolledtext.ScrolledText(
            right,
            height=18,
            bg="#0f1a22",
            fg="#edf4f8",
            insertbackground="white",
            font=("Consolas", 10),
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.results_box.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))
        self.results_box.insert(tk.END, "Select an unseen image to begin.\n")
        self.results_box.configure(state=tk.DISABLED)

        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            fg="#c8d3dc",
            bg="#101820",
            anchor="w",
            font=("Segoe UI", 10),
        )
        status.pack(fill=tk.X, padx=20, pady=(0, 12))

    def load_model_async(self):
        Thread(target=self.load_model, daemon=True).start()

    def load_model(self):
        if not MODEL_PATH.exists():
            self.set_status(f"Model not found: {MODEL_PATH}")
            self.root.after(0, lambda: messagebox.showerror("Model Missing", f"Model not found: {MODEL_PATH}"))
            return

        self.set_status("Loading YOLO model...")
        self.model = YOLO(str(MODEL_PATH))
        self.set_status("Model loaded. Drop an image or click Browse.")
        self.root.after(0, self.update_run_button)

    def browse_image(self):
        file_path = filedialog.askopenfilename(
            title="Select an unseen image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")],
        )
        if file_path:
            self.set_image(Path(file_path))

    def handle_drop(self, event):
        file_path = self.root.tk.splitlist(event.data)[0]
        self.set_image(Path(file_path))

    def set_image(self, path):
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            messagebox.showwarning("Invalid File", "Please select a JPG, PNG, BMP, or WEBP image.")
            return
        if not path.exists():
            messagebox.showerror("File Missing", f"Image not found: {path}")
            return

        self.current_image = path
        self.path_var.set(str(path))
        self.show_image(path)
        self.set_results("Ready. Click Run Inference.\n")
        self.set_status("Image selected. Run inference when ready.")
        self.update_run_button()

    def show_image(self, path):
        image = Image.open(path)
        image.thumbnail((620, 520))
        self.preview_image = ImageTk.PhotoImage(image)
        self.drop_area.configure(image=self.preview_image, text="", compound=tk.CENTER)

    def run_inference_async(self):
        if not self.current_image or not self.model:
            return

        self.run_btn.configure(state=tk.DISABLED)
        self.set_status("Running inference...")
        self.set_results("Running inference, please wait...\n")
        Thread(target=self.run_inference, daemon=True).start()

    def run_inference(self):
        try:
            results = self.model.predict(source=str(self.current_image), conf=CONFIDENCE, verbose=False)
            result = results[0]
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            result.save(filename=str(OUTPUT_PATH))
            summary = self.format_detection_summary(result)
            self.root.after(0, lambda: self.show_result(summary))
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Inference Failed", str(exc)))
            self.root.after(0, lambda: self.set_status("Inference failed."))
            self.root.after(0, self.update_run_button)

    def show_result(self, summary):
        self.show_image(OUTPUT_PATH)
        self.set_results(summary)
        self.set_status(f"Inference complete. Annotated image saved to {OUTPUT_PATH}")
        self.update_run_button()

    def format_detection_summary(self, result):
        boxes = result.boxes
        lines = ["Detections to explain:\n"]

        if boxes is None or len(boxes) == 0:
            lines.append("No objects detected above the confidence threshold.\n")
            lines.append("Explain if this is correct. If not, possible causes: blur, small object, occlusion, angle, lighting, or class not in training set.\n")
            return "".join(lines)

        for index, box in enumerate(boxes, start=1):
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = [round(value, 1) for value in box.xyxy[0].tolist()]
            lines.append(f"{index}. {class_name}\n")
            lines.append(f"   confidence: {confidence:.2f}\n")
            lines.append(f"   box: [{x1}, {y1}, {x2}, {y2}]\n\n")

        return "".join(lines)

    def update_run_button(self):
        state = tk.NORMAL if self.model and self.current_image else tk.DISABLED
        self.run_btn.configure(state=state)

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def set_results(self, text):
        self.results_box.configure(state=tk.NORMAL)
        self.results_box.delete("1.0", tk.END)
        self.results_box.insert(tk.END, text)
        self.results_box.configure(state=tk.DISABLED)


def main():
    root = TkinterDnD.Tk() if TkinterDnD else tk.Tk()
    app = LiveInferenceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
