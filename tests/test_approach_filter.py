from src.approach_filter import ApproachState, ApproachTracker


def test_unknown_with_single_observation():
    tracker = ApproachTracker()
    assert tracker.observe(track_id=1, bbox_height_px=100) == ApproachState.UNKNOWN


def test_growing_bbox_is_approaching():
    tracker = ApproachTracker()
    tracker.observe(1, 100)
    tracker.observe(1, 110)
    state = tracker.observe(1, 130)
    assert state == ApproachState.APPROACHING
    assert tracker.should_alert(1, 140) is True


def test_shrinking_bbox_is_retreating_and_suppresses_alert():
    tracker = ApproachTracker()
    tracker.observe(1, 130)
    tracker.observe(1, 110)
    state = tracker.observe(1, 90)
    assert state == ApproachState.RETREATING
    assert tracker.should_alert(1, 90) is False


def test_flat_bbox_within_noise_margin_is_unknown_and_alerts():
    tracker = ApproachTracker(noise_margin=0.05)
    tracker.observe(1, 100)
    state = tracker.observe(1, 101)  # 1% change, within 5% margin
    assert state == ApproachState.UNKNOWN
    assert tracker.should_alert(1, 101) is True  # unknown defaults to alert-safe


def test_separate_tracks_are_independent():
    tracker = ApproachTracker()
    tracker.observe(1, 100)
    tracker.observe(1, 130)  # track 1 approaching
    tracker.observe(2, 130)
    tracker.observe(2, 100)  # track 2 retreating
    assert tracker.observe(1, 140) == ApproachState.APPROACHING
    assert tracker.observe(2, 90) == ApproachState.RETREATING


def test_forget_clears_history():
    tracker = ApproachTracker()
    tracker.observe(1, 100)
    tracker.observe(1, 130)
    tracker.forget(1)
    assert tracker.observe(1, 200) == ApproachState.UNKNOWN
