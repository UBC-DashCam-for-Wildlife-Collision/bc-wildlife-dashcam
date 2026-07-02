"""
Sort a species' images into usable / rejected folders by MegaDetector
confidence. Generalizes the old moose-only filter scripts to any species.

An image is "usable" if its highest-confidence detection is >= threshold,
otherwise it goes to "rejected" for manual review. This is the step where
you eyeball the rejected pile and rescue any real animals MegaDetector
missed (and check the usable pile for false positives).

Run:
    python scripts/sort-by-confidence.py <species> <detections.json> <source_dir>

Example:
    python scripts/sort-by-confidence.py moose \\
        "/Volumes/Deepansh's SSD/bc-dashcam/detections/moose_detections.json" \\
        "/Volumes/Deepansh's SSD/bc-dashcam/data/moose"
"""

import json
import os
import shutil
import sys

CONF_THRESHOLD = 0.5


def sort_species(species, json_path, source_dir):
    usable_dir = os.path.join(source_dir, "usable")
    rejected_dir = os.path.join(source_dir, "rejected")
    os.makedirs(usable_dir, exist_ok=True)
    os.makedirs(rejected_dir, exist_ok=True)

    with open(json_path, "r") as f:
        data = json.load(f)

    usable = 0
    rejected = 0
    for image in data["images"]:
        detections = image.get("detections") or []
        max_conf = max((d["conf"] for d in detections), default=0.0)
        filename = os.path.basename(image["file"])
        src = os.path.join(source_dir, filename)
        if not os.path.exists(src):
            continue

        if max_conf >= CONF_THRESHOLD:
            shutil.copy2(src, usable_dir)
            usable += 1
        else:
            shutil.copy2(src, rejected_dir)
            rejected += 1

    total = usable + rejected
    pct = (usable / total * 100) if total else 0
    print(f"{species}: {usable} usable, {rejected} rejected ({pct:.1f}% usable)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python scripts/sort-by-confidence.py "
              "<species> <detections.json> <source_dir>")
        sys.exit(1)
    sort_species(sys.argv[1], sys.argv[2], sys.argv[3])
