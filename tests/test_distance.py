import pytest

from src.distance import BBoxSample, fused_distance_m, thin_lens_distance_m, ttc_distance_m


def test_thin_lens_basic():
    # A 1m-tall object appearing 100px tall with a 1000px focal length -> 10m away.
    assert thin_lens_distance_m(bbox_height_px=100, shoulder_height_m=1.0, focal_length_px=1000) == 10.0


def test_thin_lens_rejects_non_positive_height():
    with pytest.raises(ValueError):
        thin_lens_distance_m(bbox_height_px=0, shoulder_height_m=1.0, focal_length_px=1000)


def test_ttc_growing_bbox_returns_distance():
    prev = BBoxSample(timestamp_s=0.0, bbox_height_px=100)
    curr = BBoxSample(timestamp_s=0.1, bbox_height_px=110)
    result = ttc_distance_m(prev, curr, vehicle_speed_mps=27.0)  # ~97 km/h
    assert result is not None
    assert result > 0


def test_ttc_shrinking_bbox_returns_none():
    prev = BBoxSample(timestamp_s=0.0, bbox_height_px=110)
    curr = BBoxSample(timestamp_s=0.1, bbox_height_px=100)
    assert ttc_distance_m(prev, curr, vehicle_speed_mps=27.0) is None


def test_fusion_takes_the_minimum():
    assert fused_distance_m(thin_lens_m=50.0, ttc_m=30.0) == 30.0
    assert fused_distance_m(thin_lens_m=20.0, ttc_m=30.0) == 20.0


def test_fusion_falls_back_to_thin_lens_when_ttc_unavailable():
    assert fused_distance_m(thin_lens_m=42.0, ttc_m=None) == 42.0
