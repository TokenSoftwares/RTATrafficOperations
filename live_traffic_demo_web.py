"""Traffic capstone web demo for the reusable :class:`Detector` service.

This module demonstrates vehicle detection only. The same ``get_detector()``
factory can later be imported by simulators and edge nodes without changes.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template_string, request, send_from_directory
from werkzeug.utils import secure_filename

from traffic_detection import DetectionResult, Detector, Vehicle


DEFAULT_PORT = 5001
UPLOAD_DIR = Path("runs/traffic_demo/uploads")
RESULT_DIR = Path("runs/traffic_demo/results")
CONFIDENCE = 0.25
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def create_detector() -> Detector:
    """Build a detector instance for demos, simulators, or edge nodes."""
    return Detector(
        model_name=Detector.DEFAULT_MODEL,
        confidence=CONFIDENCE,
        device="cpu",
    )


_detector: Detector | None = None


def get_detector() -> Detector:
    """Return a shared loaded detector instance."""
    global _detector
    if _detector is None:
        _detector = create_detector()
        _detector.load()
    return _detector


def vehicles_to_json(vehicles: tuple[Vehicle, ...]) -> list[dict]:
    return [vehicle.to_dict() for vehicle in vehicles]


def result_to_json(result: DetectionResult, *, image_url: str | None = None) -> dict:
    payload = result.to_dict()
    if image_url:
        payload["image_url"] = image_url
    return payload


app = Flask(__name__)


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Edge Mesh — Vehicle Detection</title>
  <style>
    :root { color-scheme: dark; }
    body {
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: radial-gradient(circle at top left, #1f3d52, #0b1118 45%, #06090d);
      color: #edf5fb;
      min-height: 100vh;
    }
    main { max-width: 1180px; margin: 0 auto; padding: 34px 22px 46px; }
    header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-end; margin-bottom: 22px; }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 4vw, 48px); letter-spacing: -1px; }
    p { margin: 0; color: #afc4d2; line-height: 1.5; }
    .model { padding: 10px 14px; border: 1px solid #385568; border-radius: 999px; color: #cce2ef; background: rgba(11, 22, 31, .7); white-space: nowrap; font-size: 14px; }
    .grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(320px, .8fr); gap: 20px; }
    .card { background: rgba(16, 29, 39, .78); border: 1px solid rgba(107, 148, 172, .24); border-radius: 24px; box-shadow: 0 24px 70px rgba(0, 0, 0, .32); }
    #dropzone { min-height: 420px; display: grid; place-items: center; text-align: center; padding: 28px; border: 2px dashed #5f879d; transition: .16s ease; cursor: pointer; }
    #dropzone.dragover { border-color: #54d98c; background: rgba(39, 174, 96, .12); transform: translateY(-2px); }
    .drop-title { font-size: 28px; font-weight: 800; margin-bottom: 10px; }
    .drop-subtitle { color: #b9ccd7; }
    #preview { width: 100%; max-height: 620px; object-fit: contain; border-radius: 20px; display: none; }
    aside { padding: 20px; }
    button { width: 100%; border: 0; border-radius: 14px; padding: 14px 16px; color: white; background: #2f80ed; font-weight: 800; font-size: 16px; cursor: pointer; }
    button:disabled { cursor: not-allowed; background: #465765; color: #9fb2be; }
    .status { margin: 16px 0; color: #c7d8e2; min-height: 24px; }
    .predictions { display: grid; gap: 10px; margin-top: 12px; }
    .prediction { padding: 12px; border-radius: 14px; background: #0d1922; border: 1px solid #213646; }
    .prediction strong { display: block; font-size: 18px; margin-bottom: 6px; color: #ffffff; }
    .muted { color: #9fb4c2; font-size: 14px; }
    .meta { margin-top: 14px; padding: 12px; border-radius: 14px; background: rgba(47, 128, 237, .12); border: 1px solid rgba(47, 128, 237, .28); color: #d9ebff; font-size: 14px; }
    input { display: none; }
    @media (max-width: 860px) { header { display: block; } .model { display: inline-block; margin-top: 14px; } .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>AI Edge Mesh — Vehicle Detection</h1>
        <p>Milestone 1: pretrained YOLO vehicle detection through the reusable Detector service.</p>
        <p>Upload an intersection or road image to receive structured Vehicle objects for downstream edge nodes.</p>
      </div>
      <div class="model">Model: {{ model_name }}</div>
    </header>

    <section class="grid">
      <div id="dropzone" class="card">
        <div id="dropcopy">
          <div class="drop-title">Drag and drop image here</div>
          <div class="drop-subtitle">or click to choose JPG, PNG, BMP, or WEBP</div>
        </div>
        <img id="preview" alt="Detection result">
        <input id="fileInput" type="file" accept="image/*">
      </div>

      <aside class="card">
        <button id="runButton" disabled>Run Detection</button>
        <div id="status" class="status">Choose a road or intersection image to begin.</div>
        <div class="muted" id="fileName"></div>
        <div id="meta" class="meta" style="display:none;"></div>
        <div id="predictions" class="predictions"></div>
      </aside>
    </section>
  </main>

  <script>
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const runButton = document.getElementById('runButton');
    const statusBox = document.getElementById('status');
    const fileName = document.getElementById('fileName');
    const metaBox = document.getElementById('meta');
    const predictions = document.getElementById('predictions');
    const preview = document.getElementById('preview');
    const dropcopy = document.getElementById('dropcopy');
    let selectedFile = null;

    function setFile(file) {
      if (!file) return;
      selectedFile = file;
      fileName.textContent = file.name;
      statusBox.textContent = 'Ready. Click Run Detection.';
      predictions.innerHTML = '';
      metaBox.style.display = 'none';
      runButton.disabled = false;
      preview.src = URL.createObjectURL(file);
      preview.style.display = 'block';
      dropcopy.style.display = 'none';
    }

    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => setFile(fileInput.files[0]));
    dropzone.addEventListener('dragover', (event) => { event.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (event) => {
      event.preventDefault();
      dropzone.classList.remove('dragover');
      setFile(event.dataTransfer.files[0]);
    });

    runButton.addEventListener('click', async () => {
      if (!selectedFile) return;
      runButton.disabled = true;
      statusBox.textContent = 'Running detection...';
      predictions.innerHTML = '';
      metaBox.style.display = 'none';

      const formData = new FormData();
      formData.append('image', selectedFile);

      try {
        const response = await fetch('/detect', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Detection failed');

        preview.src = data.image_url + '?t=' + Date.now();
        statusBox.textContent = `Detection complete. ${data.vehicle_count} vehicle(s).`;
        metaBox.style.display = 'block';
        metaBox.innerHTML = `
          Inference: ${data.inference_ms} ms<br>
          Image size: ${data.image_width} x ${data.image_height}<br>
          Model: ${data.model_name}
        `;

        if (data.vehicles.length === 0) {
          predictions.innerHTML = '<div class="prediction">No vehicles detected above the confidence threshold.</div>';
        } else {
          predictions.innerHTML = data.vehicles.map((vehicle) => `
            <div class="prediction">
              <strong>#${vehicle.id} ${vehicle.type}</strong>
              confidence: ${vehicle.confidence.toFixed(2)}<br>
              <span class="muted">bbox: [${vehicle.bbox.join(', ')}]</span><br>
              <span class="muted">center: [${vehicle.center.join(', ')}]</span>
            </div>
          `).join('');
        }
      } catch (error) {
        statusBox.textContent = error.message;
      } finally {
        runButton.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.get("/")
def index():
    detector = get_detector()
    return render_template_string(PAGE, model_name=detector.model_name)


@app.post("/detect")
def detect():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    image = request.files["image"]
    if not image.filename or not allowed_file(image.filename):
        return jsonify({"error": "Upload a JPG, PNG, BMP, or WEBP image."}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(image.filename).suffix.lower()
    safe_name = secure_filename(Path(image.filename).stem) or "image"
    token = uuid4().hex[:10]
    upload_path = UPLOAD_DIR / f"{safe_name}_{token}{suffix}"
    result_path = RESULT_DIR / f"{safe_name}_{token}.jpg"
    image.save(upload_path)

    detection = get_detector().detect(
        upload_path,
        save_annotated_to=result_path,
    )

    payload = result_to_json(
        detection,
        image_url=f"/results/{result_path.name}",
    )
    return jsonify(payload)


@app.get("/results/<path:filename>")
def result_file(filename: str):
    return send_from_directory(RESULT_DIR, filename)


if __name__ == "__main__":
    get_detector()
    print(f"Open this URL in your browser: http://127.0.0.1:{DEFAULT_PORT}")
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=False)
