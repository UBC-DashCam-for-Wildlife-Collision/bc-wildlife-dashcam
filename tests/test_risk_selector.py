from src.config import load_species_table
from src.risk_selector import Detection, select_alert_detection


def test_empty_list_returns_none():
    table = load_species_table()
    assert select_alert_detection([], table) is None


def test_picks_highest_risk_tier():
    table = load_species_table()
    detections = [
        Detection(track_id=1, label="raccoon", confidence=0.9, distance_m=10.0),  # low risk, close
        Detection(track_id=2, label="moose", confidence=0.6, distance_m=70.0),  # critical risk, far
    ]
    chosen = select_alert_detection(detections, table)
    assert chosen.label == "moose"


def test_ties_broken_by_closest_distance():
    table = load_species_table()
    detections = [
        Detection(track_id=1, label="bear", confidence=0.8, distance_m=50.0),  # both high risk
        Detection(track_id=2, label="deer", confidence=0.8, distance_m=20.0),
    ]
    chosen = select_alert_detection(detections, table)
    assert chosen.label == "deer"


def test_single_detection_returned_as_is():
    table = load_species_table()
    detections = [Detection(track_id=1, label="coyote", confidence=0.7, distance_m=30.0)]
    assert select_alert_detection(detections, table).track_id == 1
