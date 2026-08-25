"""COCO-style mAP computation, framework-agnostic (plain lists of boxes in
and numbers out) so it can be unit-tested here on the Pi without a dataset
or the Hailo Dataflow Compiler, and reused as-is by eval_map_int8_colab.py
for the float32-vs-INT8 comparison (Phase 3's last exit criterion, see
CLAUDE.md section 8/9 and docs/meeting_log.md Aug 12 entry).

Boxes are (x1, y1, x2, y2) in the same coordinate space (normalized 0-1 or
pixels, as long as predictions and ground truth agree). AP per class uses
101-point interpolation, matching COCO/ultralytics convention so numbers
here are comparable to the float32 mAP50/mAP50-95 already recorded from
training (CLAUDE.md section 8: mAP50 0.823, mAP50-95 0.638).
"""

from dataclasses import dataclass

Box = tuple[float, float, float, float]


@dataclass
class Detection:
    image_id: str
    class_id: int
    box: Box
    score: float


@dataclass
class GroundTruth:
    image_id: str
    class_id: int
    box: Box


def iou(a: Box, b: Box) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _ap_101point(recalls: list[float], precisions: list[float]) -> float:
    """Standard COCO 101-point interpolated AP."""
    if not recalls:
        return 0.0
    interp = []
    for r_thresh in [i / 100 for i in range(101)]:
        p_at_or_above = [p for r, p in zip(recalls, precisions) if r >= r_thresh]
        interp.append(max(p_at_or_above) if p_at_or_above else 0.0)
    return sum(interp) / len(interp)


def average_precision_for_class(
    detections: list[Detection],
    ground_truths: list[GroundTruth],
    class_id: int,
    iou_threshold: float,
) -> float:
    """AP for one class at one IoU threshold."""
    class_dets = sorted(
        (d for d in detections if d.class_id == class_id), key=lambda d: d.score, reverse=True
    )
    gts_by_image: dict[str, list[GroundTruth]] = {}
    for gt in ground_truths:
        if gt.class_id == class_id:
            gts_by_image.setdefault(gt.image_id, []).append(gt)
    num_gt = sum(len(v) for v in gts_by_image.values())
    if num_gt == 0:
        return 0.0

    matched: dict[str, set[int]] = {img: set() for img in gts_by_image}
    tp = [0] * len(class_dets)
    fp = [0] * len(class_dets)

    for i, det in enumerate(class_dets):
        candidates = gts_by_image.get(det.image_id, [])
        best_iou, best_idx = 0.0, -1
        for idx, gt in enumerate(candidates):
            if idx in matched.get(det.image_id, set()):
                continue
            cur_iou = iou(det.box, gt.box)
            if cur_iou > best_iou:
                best_iou, best_idx = cur_iou, idx
        if best_iou >= iou_threshold and best_idx >= 0:
            matched[det.image_id].add(best_idx)
            tp[i] = 1
        else:
            fp[i] = 1

    tp_cum = _cumsum(tp)
    fp_cum = _cumsum(fp)
    recalls = [t / num_gt for t in tp_cum]
    precisions = [t / (t + f) if (t + f) > 0 else 0.0 for t, f in zip(tp_cum, fp_cum)]
    return _ap_101point(recalls, precisions)


def _cumsum(xs: list[int]) -> list[int]:
    out, total = [], 0
    for x in xs:
        total += x
        out.append(total)
    return out


def compute_map(
    detections: list[Detection],
    ground_truths: list[GroundTruth],
    num_classes: int,
) -> dict[str, float | dict[int, float]]:
    """mAP50 (IoU 0.5) and mAP50-95 (IoU 0.5:0.05:0.95, COCO convention),
    plus per-class AP50, matching the metrics CLAUDE.md already reports for
    the float32 model so the INT8 numbers are directly comparable.
    """
    iou_thresholds = [0.5 + 0.05 * i for i in range(10)]  # 0.50 .. 0.95

    per_class_ap50: dict[int, float] = {}
    per_class_ap_all: dict[int, list[float]] = {}
    for class_id in range(num_classes):
        aps = [
            average_precision_for_class(detections, ground_truths, class_id, thresh)
            for thresh in iou_thresholds
        ]
        per_class_ap_all[class_id] = aps
        per_class_ap50[class_id] = aps[0]

    classes_with_gt = [c for c in range(num_classes) if any(gt.class_id == c for gt in ground_truths)]
    if not classes_with_gt:
        return {"map50": 0.0, "map50_95": 0.0, "per_class_ap50": per_class_ap50}

    map50 = sum(per_class_ap50[c] for c in classes_with_gt) / len(classes_with_gt)
    map50_95 = sum(sum(per_class_ap_all[c]) / len(iou_thresholds) for c in classes_with_gt) / len(
        classes_with_gt
    )
    return {"map50": map50, "map50_95": map50_95, "per_class_ap50": per_class_ap50}
