from src.config import load_zone_table
from src.zones import classify_zone


def test_far_distance_is_zone1():
    table = load_zone_table()
    zone = classify_zone(120.0, table)
    assert zone.name == "zone1"


def test_mid_distance_is_zone2():
    table = load_zone_table()
    zone = classify_zone(60.0, table)
    assert zone.name == "zone2"


def test_close_distance_is_zone3():
    table = load_zone_table()
    zone = classify_zone(10.0, table)
    assert zone.name == "zone3"


def test_boundary_at_80m_is_zone2_not_zone1():
    # min_distance_m for zone2 is 40, zone1 is 80: exactly 80m should
    # satisfy zone1's threshold (distance >= min_distance_m), i.e. still log-only.
    table = load_zone_table()
    zone = classify_zone(80.0, table)
    assert zone.name == "zone1"


def test_just_under_80m_is_zone2():
    table = load_zone_table()
    zone = classify_zone(79.9, table)
    assert zone.name == "zone2"


def test_zero_distance_is_zone3():
    table = load_zone_table()
    zone = classify_zone(0.0, table)
    assert zone.name == "zone3"
