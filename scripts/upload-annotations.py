"""
Upload MegaDetector bounding boxes to Roboflow (LEGACY / SUPERSEDED).

Kept for reference only. The canonical dataset now builds locally via
scripts/build-yolo-dataset.py, and augmentation happens online during
YOLOv8 training, so Roboflow is no longer in the pipeline.

If you ever do use this: the Roboflow API will render "?" placeholder
labels unless the 7 class names already exist in the project. Create them
in the Classes and Tags panel first, then run this.

The API key is read from the environment, never hardcoded:
    export ROBOFLOW_API_KEY=your_key_here
    python scripts/upload-annotations.py
"""

import json
import os
import time

import requests

API_KEY = os.environ.get("ROBOFLOW_API_KEY")
if not API_KEY:
    raise SystemExit("Set ROBOFLOW_API_KEY in your environment first.")

WORKSPACE = "deepanshs-workspace"
PROJECT = "bc-wildlife-dashcam"

JSON_PATHS = [
    "detections/wildlife_positives_clean_md_results.json",
    "detections/moose_detections.json",
]

CLASSES = {"bear", "cougar", "coyote", "deer", "elk", "moose", "raccoon"}

uploaded = skipped = errors = 0

for json_path in JSON_PATHS:
    print(f"\nProcessing: {os.path.basename(json_path)}")
    with open(json_path, "r") as f:
        data = json.load(f)

    for img in data["images"]:
        parts = img["file"].replace("\\", "/").split("/")
        species = parts[-2] if len(parts) >= 2 else ""
        if species not in CLASSES:
            skipped += 1
            continue

        detections = img.get("detections") or []
        if not detections:
            skipped += 1
            continue

        best = max(detections, key=lambda d: d["conf"])
        if best["conf"] < 0.5:
            skipped += 1
            continue

        x, y, w, h = best["bbox"]
        x_center = x + w / 2
        y_center = y + h / 2
        filename = parts[-1]

        url = f"https://api.roboflow.com/{WORKSPACE}/{PROJECT}/image/annotate"
        annotation_data = {
            "api_key": API_KEY,
            "name": filename,
            "annotation": json.dumps({
                "boxes": [{
                    "label": species,
                    "x": round(x_center * 100, 4),
                    "y": round(y_center * 100, 4),
                    "width": round(w * 100, 4),
                    "height": round(h * 100, 4),
                }]
            }),
        }

        try:
            response = requests.post(url, data=annotation_data)
            if response.status_code == 200:
                uploaded += 1
            else:
                errors += 1
                if errors <= 5:
                    print(f"Error on {filename}: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"Exception on {filename}: {e}")

        time.sleep(0.05)
        if uploaded % 100 == 0 and uploaded > 0:
            print(f"Progress: {uploaded} uploaded, {skipped} skipped, {errors} errors")

print(f"\nDone: {uploaded} uploaded, {skipped} skipped, {errors} errors")
