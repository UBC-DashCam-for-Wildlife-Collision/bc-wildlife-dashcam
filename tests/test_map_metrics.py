import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.map_eval.metrics import Detection, GroundTruth, average_precision_for_class, compute_map, iou


def test_iou_identical_boxes_is_one():
    box = (0.1, 0.1, 0.5, 0.5)
    assert iou(box, box) == 1.0


def test_iou_disjoint_boxes_is_zero():
    assert iou((0.0, 0.0, 0.1, 0.1), (0.5, 0.5, 0.6, 0.6)) == 0.0


def test_iou_known_overlap():
    # two unit squares overlapping by a 0.5x1 rectangle -> intersection 0.5,
    # union 1.5 -> IoU 1/3
    a = (0.0, 0.0, 1.0, 1.0)
    b = (0.5, 0.0, 1.5, 1.0)
    assert abs(iou(a, b) - (1 / 3)) < 1e-9


def test_perfect_detections_give_ap_one():
    gts = [GroundTruth("img1", 0, (0.0, 0.0, 1.0, 1.0)), GroundTruth("img2", 0, (0.0, 0.0, 1.0, 1.0))]
    dets = [
        Detection("img1", 0, (0.0, 0.0, 1.0, 1.0), 0.9),
        Detection("img2", 0, (0.0, 0.0, 1.0, 1.0), 0.9),
    ]
    ap = average_precision_for_class(dets, gts, class_id=0, iou_threshold=0.5)
    assert ap == 1.0


def test_no_detections_gives_ap_zero():
    gts = [GroundTruth("img1", 0, (0.0, 0.0, 1.0, 1.0))]
    ap = average_precision_for_class([], gts, class_id=0, iou_threshold=0.5)
    assert ap == 0.0


def test_no_ground_truth_gives_ap_zero_not_crash():
    dets = [Detection("img1", 0, (0.0, 0.0, 1.0, 1.0), 0.9)]
    ap = average_precision_for_class(dets, [], class_id=0, iou_threshold=0.5)
    assert ap == 0.0


def test_false_positive_only_gives_low_ap():
    gts = [GroundTruth("img1", 0, (0.0, 0.0, 1.0, 1.0))]
    # detection is in the wrong place entirely -- no overlap with ground truth
    dets = [Detection("img1", 0, (5.0, 5.0, 6.0, 6.0), 0.9)]
    ap = average_precision_for_class(dets, gts, class_id=0, iou_threshold=0.5)
    assert ap == 0.0


def test_compute_map_matches_hand_computed_perfect_case():
    gts = [
        GroundTruth("img1", 0, (0.0, 0.0, 1.0, 1.0)),
        GroundTruth("img1", 1, (0.0, 0.0, 0.5, 0.5)),
    ]
    dets = [
        Detection("img1", 0, (0.0, 0.0, 1.0, 1.0), 0.95),
        Detection("img1", 1, (0.0, 0.0, 0.5, 0.5), 0.95),
    ]
    result = compute_map(dets, gts, num_classes=2)
    assert result["map50"] == 1.0
    assert result["map50_95"] == 1.0
    assert result["per_class_ap50"][0] == 1.0
    assert result["per_class_ap50"][1] == 1.0


def test_compute_map_partial_iou_hurts_map50_95_more_than_map50():
    # box is offset just enough to still clear IoU 0.5 but fail the tighter
    # 0.75+ thresholds baked into mAP50-95's average
    gt = GroundTruth("img1", 0, (0.0, 0.0, 1.0, 1.0))
    det = Detection("img1", 0, (0.2, 0.0, 1.2, 1.0), 0.9)  # IoU = 0.8/1.2 = 0.667
    result = compute_map([det], [gt], num_classes=1)
    assert result["map50"] == 1.0  # clears IoU 0.5
    assert result["map50_95"] < result["map50"]  # fails some of the 0.55..0.95 thresholds
