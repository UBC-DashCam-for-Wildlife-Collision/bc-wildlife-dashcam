"""
Build a YOLOv8 dataset locally from MegaDetector detection JSONs.

This is the canonical dataset builder. It reads the MegaDetector output,
keeps the highest-confidence detection per image (conf >= threshold),
converts the bbox from MegaDetector's corner format to YOLO's center
format, splits into train/valid/test at a fixed seed, and writes the
folder layout plus data.yaml that Ultralytics expects.

MegaDetector bboxes are already normalized to 0-1, so the only geometry
change is corner -> center for x and y. Width and height pass through.

Run:
    python scripts/build-yolo-dataset.py

Output:
    OUTPUT_DIR/
        data.yaml
        train/images/  train/labels/
        valid/images/  valid/labels/
        test/images/   test/labels/
"""

import json
import os
import shutil
import random

# --- Configuration -------------------------------------------------
# Point these at wherever the species image folders and detection JSONs
# live. Defaults assume the T7 SSD layout.
IMAGE_ROOT = "/Volumes/Deepansh's SSD/bc-dashcam/data"
OUTPUT_DIR = "/Volumes/Deepansh's SSD/bc-dashcam/yolo_dataset"

JSON_PATHS = [
    "/Volumes/Deepansh's SSD/bc-dashcam/detections/wildlife_positives_clean_md_results.json",
    "/Volumes/Deepansh's SSD/bc-dashcam/detections/moose_detections.json",
]

# Alphabetical order fixes the class IDs. This MUST match the data.yaml
# ordering, so never reorder this list after training on it.
CLASSES = ["bear", "cougar", "coyote", "deer", "elk", "moose", "raccoon"]
CLASS_TO_ID = {name: i for i, name in enumerate(CLASSES)}

CONF_THRESHOLD = 0.5
SPLIT = (0.70, 0.20, 0.10)   # train, valid, test
RANDOM_SEED = 42             # fixed seed keeps the split reproducible
# -------------------------------------------------------------------

random.seed(RANDOM_SEED)


def collect_samples():
    """Return (species, filename, yolo_line) for every kept detection."""
    samples = []
    seen = set()   # dedupe if an image shows up in more than one JSON

    for json_path in JSON_PATHS:
        if not os.path.exists(json_path):
            print(f"WARNING: JSON not found, skipping: {json_path}")
            continue
        with open(json_path, "r") as f:
            data = json.load(f)

        for img in data["images"]:
            # The "file" field can be relative ("bear/x.jpg") or a full
            # Colab path ("/content/drive/.../moose/x.jpg"). Take the last
            # two components so both shapes work.
            parts = img["file"].replace("\\", "/").split("/")
            filename = parts[-1]
            species = parts[-2] if len(parts) >= 2 else ""

            if species not in CLASS_TO_ID:
                continue

            key = (species, filename)
            if key in seen:
                continue

            detections = img.get("detections") or []
            if not detections:
                continue

            best = max(detections, key=lambda d: d["conf"])
            if best["conf"] < CONF_THRESHOLD:
                continue

            x_min, y_min, w, h = best["bbox"]
            x_center = x_min + w / 2.0
            y_center = y_min + h / 2.0

            # Clamp to guard against rounding spillover past the edges.
            x_center = min(max(x_center, 0.0), 1.0)
            y_center = min(max(y_center, 0.0), 1.0)
            w = min(max(w, 0.0), 1.0)
            h = min(max(h, 0.0), 1.0)

            class_id = CLASS_TO_ID[species]
            yolo_line = f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}"

            seen.add(key)
            samples.append((species, filename, yolo_line))

    return samples


def split_samples(samples):
    """Shuffle once, then slice by ratio."""
    random.shuffle(samples)
    n = len(samples)
    n_train = int(n * SPLIT[0])
    n_valid = int(n * SPLIT[1])
    return {
        "train": samples[:n_train],
        "valid": samples[n_train:n_train + n_valid],
        "test":  samples[n_train + n_valid:],
    }


def make_dirs():
    for split in ("train", "valid", "test"):
        os.makedirs(os.path.join(OUTPUT_DIR, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, split, "labels"), exist_ok=True)


def write_split(split_name, items):
    copied = 0
    missing = 0
    for species, filename, yolo_line in items:
        src_img = os.path.join(IMAGE_ROOT, species, filename)
        if not os.path.exists(src_img):
            missing += 1
            if missing <= 5:
                print(f"  MISSING IMAGE: {src_img}")
            continue

        # Prefix with species so filenames can't collide across classes.
        out_stem = f"{species}-{os.path.splitext(filename)[0]}"
        dst_img = os.path.join(OUTPUT_DIR, split_name, "images", out_stem + ".jpg")
        dst_lbl = os.path.join(OUTPUT_DIR, split_name, "labels", out_stem + ".txt")

        shutil.copy2(src_img, dst_img)
        with open(dst_lbl, "w") as lf:
            lf.write(yolo_line + "\n")
        copied += 1

    print(f"  {split_name}: {copied} copied, {missing} missing")
    return copied


def write_data_yaml():
    yaml_path = os.path.join(OUTPUT_DIR, "data.yaml")
    lines = [
        f"path: {OUTPUT_DIR}",
        "train: train/images",
        "val: valid/images",
        "test: test/images",
        "",
        f"nc: {len(CLASSES)}",
        f"names: {CLASSES}",
        "",
    ]
    with open(yaml_path, "w") as f:
        f.write("\n".join(lines))
    print(f"\ndata.yaml written to {yaml_path}")


def main():
    print("Collecting samples...")
    samples = collect_samples()
    print(f"Total usable samples: {len(samples)}")

    counts = {c: 0 for c in CLASSES}
    for species, _, _ in samples:
        counts[species] += 1
    print("Per-class counts:")
    for c in CLASSES:
        print(f"  {c}: {counts[c]}")

    make_dirs()
    splits = split_samples(samples)

    print("\nWriting splits...")
    total = 0
    for split_name in ("train", "valid", "test"):
        total += write_split(split_name, splits[split_name])

    write_data_yaml()
    print(f"\nDone. {total} images written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
