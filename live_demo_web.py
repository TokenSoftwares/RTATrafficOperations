from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template_string, request, send_from_directory
from ultralytics import YOLO
from werkzeug.utils import secure_filename


FINAL_MODEL_PATH = Path("final_weights/best.pt")
MODEL_PATH = FINAL_MODEL_PATH if FINAL_MODEL_PATH.exists() else Path("models/best.pt")
UPLOAD_DIR = Path("runs/web_demo/uploads")
RESULT_DIR = Path("runs/web_demo/results")
CONFIDENCE = 0.30
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


app = Flask(__name__)
model = None


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Smart Campus Device Detection</title>
  <style>
    :root { color-scheme: dark; }
    body {
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: radial-gradient(circle at top left, #24465d, #0c1218 45%, #070a0e);
      color: #edf5fb;
      min-height: 100vh;
    }
    main { max-width: 1180px; margin: 0 auto; padding: 34px 22px 46px; }
    header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-end; margin-bottom: 22px; }
    h1 { margin: 0 0 8px; font-size: clamp(30px, 4vw, 52px); letter-spacing: -1.5px; }
    p { margin: 0; color: #afc4d2; line-height: 1.5; }
    .model { padding: 10px 14px; border: 1px solid #385568; border-radius: 999px; color: #cce2ef; background: rgba(11, 22, 31, .7); white-space: nowrap; }
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
    .script { margin-top: 18px; padding: 14px; border-radius: 16px; background: rgba(84, 217, 140, .1); border: 1px solid rgba(84, 217, 140, .28); color: #dfffea; }
    input { display: none; }
    @media (max-width: 860px) { header { display: block; } .model { display: inline-block; margin-top: 14px; } .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Smart Campus Device Detection</h1>
        <p>Drop an image, run YOLO inference, and present bounding boxes, confidence scores, and class predictions.</p>
        <p>Done by Saleh Dweik - 20230003058, Mohammad Jaafrie - 20220001221, Xavier - 20230003339, Rithik Manohar - 20220002309, and Abir Hossain - 20220001382.</p>
      </div>
      <div class="model">Model: {{ model_path }}</div>
    </header>

    <section class="grid">
      <div id="dropzone" class="card">
        <div id="dropcopy">
          <div class="drop-title">Drag and drop image here</div>
          <div class="drop-subtitle">or click to choose JPG, PNG, BMP, or WEBP</div>
        </div>
        <img id="preview" alt="Inference result">
        <input id="fileInput" type="file" accept="image/*">
      </div>

      <aside class="card">
        <button id="runButton" disabled>Run Inference</button>
        <div id="status" class="status">Choose an unseen image to begin.</div>
        <div class="muted" id="fileName"></div>
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
    const predictions = document.getElementById('predictions');
    const preview = document.getElementById('preview');
    const dropcopy = document.getElementById('dropcopy');
    let selectedFile = null;

    function setFile(file) {
      if (!file) return;
      selectedFile = file;
      fileName.textContent = file.name;
      statusBox.textContent = 'Ready. Click Run Inference.';
      predictions.innerHTML = '';
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
      statusBox.textContent = 'Running inference...';
      predictions.innerHTML = '';

      const formData = new FormData();
      formData.append('image', selectedFile);

      try {
        const response = await fetch('/predict', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Inference failed');

        preview.src = data.image_url + '?t=' + Date.now();
        statusBox.textContent = `Inference complete. ${data.detections.length} detection(s).`;
        if (data.detections.length === 0) {
          predictions.innerHTML = '<div class="prediction">No objects detected above confidence threshold.<br><span class="muted">Possible causes include blur, a small object, occlusion, lighting, or a class outside the training set.</span></div>';
        } else {
          predictions.innerHTML = data.detections.map((d, index) => `
            <div class="prediction">
              <strong>${index + 1}. ${d.class_name}</strong>
              confidence: ${d.confidence.toFixed(2)}<br>
              <span class="muted">box: [${d.box.join(', ')}]</span>
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


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def load_model():
    global model
    if model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
        model = YOLO(str(MODEL_PATH))
    return model


@app.get("/")
def index():
    return render_template_string(PAGE, model_path=MODEL_PATH.as_posix())


@app.post("/predict")
def predict():
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

    result = load_model().predict(source=str(upload_path), conf=CONFIDENCE, verbose=False)[0]
    result.save(filename=str(result_path))

    detections = []
    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls[0])
            detections.append(
                {
                    "class_name": result.names[class_id],
                    "confidence": float(box.conf[0]),
                    "box": [round(value, 1) for value in box.xyxy[0].tolist()],
                }
            )

    return jsonify(
        {
            "detections": detections,
            "image_url": f"/results/{result_path.name}",
            "model_path": MODEL_PATH.as_posix(),
        }
    )


@app.get("/results/<path:filename>")
def result_file(filename):
    return send_from_directory(RESULT_DIR, filename)


if __name__ == "__main__":
    load_model()
    print("Open this URL in your browser: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
