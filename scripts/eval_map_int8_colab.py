#!/usr/bin/env python3
"""Float32-vs-INT8 mAP comparison -- Phase 3's last exit criterion
(CLAUDE.md sections 8/9; docs/meeting_log.md, Aug 12 2026 entry: "mAP
degradation measurement (float32 vs INT8) is now the sole remaining Phase
3 exit criterion").

RUN THIS ON COLAB (the Hailo Dataflow Compiler + the held-out test split),
NOT on the Pi -- the raw dataset never goes on the Pi (CLAUDE.md section 7)
and the Pi doesn't have hailo_sdk_client (only the lighter hailo_platform
runtime for running an already-compiled .hef). Same environment as the
Aug 12 2026 quantization session: Colab Pro, GPU + High-RAM runtime,
hailo_env with hailo_sdk_client installed.

    runner = ClientRunner(har=".../bc_dashcam_yolov8n_quantized.har")
    # this .har is the already-quantized one from the Aug 12 session,
    # loaded fresh here rather than re-run through optimize()

Usage (inside that Colab session, repo cloned, SSD's yolo_dataset mounted):

    python3 scripts/eval_map_int8_colab.py \\
        --har /path/to/bc_dashcam_yolov8n_quantized.har \\
        --test-images /path/to/yolo_dataset/test/images \\
        --test-labels /path/to/yolo_dataset/test/labels \\
        --num-classes 7

Ground truth is read from YOLO-format label .txt files (one per image,
same basename, lines "class_id x_center y_center width height" normalized
0-1) -- the format scripts/build-yolo-dataset.py already produces for this
project's val/test split.

This script has NOT been run end-to-end yet (written on the Pi, which has
neither hailo_sdk_client nor the dataset -- see class docstring above).
Sanity-check the float32 (SDK_NATIVE) mAP50/mAP50-95 this prints against
the already-known ultralytics numbers (CLAUDE.md section 8: mAP50 0.823,
mAP50-95 0.638) before trusting the INT8 (SDK_QUANTIZED) side -- if native
doesn't roughly match, something about the eval harness itself (box
coordinate convention, label parsing, class index mapping) is wrong before
INT8 numbers can be trusted either.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.map_eval.metrics import Detection, GroundTruth, compute_map  # noqa: E402


def load_yolo_ground_truth(labels_dir: Path, image_ids: list[str]) -> list[GroundTruth]:
    """YOLO format is (class_id, x_center, y_center, w, h), all normalized
    0-1 -- convert to the (x1, y1, x2, y2) convention metrics.py expects.
    """
    ground_truths = []
    for image_id in image_ids:
        label_path = labels_dir / f"{image_id}.txt"
        if not label_path.exists():
            continue
        for line in label_path.read_text().splitlines():
            if not line.strip():
                continue
            class_id, xc, yc, w, h = line.split()
            class_id, xc, yc, w, h = int(class_id), float(xc), float(yc), float(w), float(h)
            box = (xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2)
            ground_truths.append(GroundTruth(image_id=image_id, class_id=class_id, box=box))
    return ground_truths


def run_inference(runner, context, image_ids: list[str], images_dir: Path) -> list[Detection]:
    """Run one inference context (SDK_NATIVE for float32, SDK_QUANTIZED for
    INT8) over the test set and collect detections in metrics.py's format.

    Uses the same NMS postprocess baked into the compiled model (classes=7,
    per models/nms_config_7class.json) -- runner.infer() with a
    post-quantization HAR returns already-NMS'd per-class boxes+scores, so
    no separate NMS step is needed here.
    """
    import numpy as np
    from PIL import Image
    from hailo_sdk_client import InferenceContext

    detections: list[Detection] = []
    for image_id in image_ids:
        image_path = next(images_dir.glob(f"{image_id}.*"))
        image = np.array(Image.open(image_path).convert("RGB").resize((640, 640)))
        batch = np.expand_dims(image, axis=0)

        with runner.infer_context(context) as ctx:
            raw_output = runner.infer(ctx, batch)

        # HailoRT NMS-postprocess output: list indexed by class, each entry
        # an array of [x1, y1, y2, x2, score] rows (or empty) -- see
        # models/bc_dashcam_yolov8n.alls for the exact postprocess config
        # this model was compiled with.
        per_class = raw_output[0] if isinstance(raw_output, (list, tuple)) else raw_output
        for class_id, class_dets in enumerate(per_class):
            for row in class_dets:
                y1, x1, y2, x2, score = row[:5]
                detections.append(
                    Detection(image_id=image_id, class_id=class_id, box=(x1, y1, x2, y2), score=float(score))
                )
    return detections


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--har", type=Path, required=True, help="Quantized .har from the Aug 12 2026 session")
    parser.add_argument("--test-images", type=Path, required=True)
    parser.add_argument("--test-labels", type=Path, required=True)
    parser.add_argument("--num-classes", type=int, default=7)
    args = parser.parse_args()

    from hailo_sdk_client import ClientRunner, InferenceContext

    image_ids = sorted(p.stem for p in args.test_images.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    print(f"Test set: {len(image_ids)} images from {args.test_images}")

    ground_truths = load_yolo_ground_truth(args.test_labels, image_ids)
    print(f"Ground truth boxes: {len(ground_truths)}")

    runner = ClientRunner(har=str(args.har))

    print("\n--- Running SDK_NATIVE (float32) inference ---")
    native_dets = run_inference(runner, InferenceContext.SDK_NATIVE, image_ids, args.test_images)
    native_result = compute_map(native_dets, ground_truths, args.num_classes)
    print(f"float32: mAP50={native_result['map50']:.4f}  mAP50-95={native_result['map50_95']:.4f}")
    print(
        "(sanity check -- should roughly match the ultralytics training numbers "
        "recorded in CLAUDE.md: mAP50 0.823, mAP50-95 0.638)"
    )

    print("\n--- Running SDK_QUANTIZED (INT8) inference ---")
    quant_dets = run_inference(runner, InferenceContext.SDK_QUANTIZED, image_ids, args.test_images)
    quant_result = compute_map(quant_dets, ground_truths, args.num_classes)
    print(f"INT8:    mAP50={quant_result['map50']:.4f}  mAP50-95={quant_result['map50_95']:.4f}")

    print("\n=== Drop (float32 - INT8) ===")
    print(f"mAP50 drop:    {native_result['map50'] - quant_result['map50']:.4f}")
    print(f"mAP50-95 drop: {native_result['map50_95'] - quant_result['map50_95']:.4f}")


if __name__ == "__main__":
    main()
