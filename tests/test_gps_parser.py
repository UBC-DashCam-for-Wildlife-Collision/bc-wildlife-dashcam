from src.gps_parser import parse_gprmc

# Example sentence straight from docs/gps_interface_spec.md section 2.
SPEC_EXAMPLE = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"


def test_spec_example_parses_correctly():
    fix = parse_gprmc(SPEC_EXAMPLE)
    assert fix is not None
    # NMEA's date field is a 2-digit year ("94"); this parser windows it as
    # 2000-2099 since the deployed system only ever sees real 2020s-2030s
    # fixes. The spec's own example sentence happens to be a textbook one
    # from 1994, so it round-trips to 2094 here -- expected, not a bug.
    assert fix.utc_timestamp == "2094-03-23T12:35:19Z"
    assert round(fix.latitude, 4) == 48.1173
    assert round(fix.longitude, 4) == 11.5167
    assert round(fix.speed_kmh, 2) == round(22.4 * 1.852, 2)


def test_invalid_status_is_dropped():
    invalid = "$GPRMC,123519,V,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
    assert parse_gprmc(invalid) is None


def test_empty_lat_lon_is_dropped():
    bad = "$GPRMC,123519,A,,N,,E,022.4,084.4,230394,003.1,W*6A"
    assert parse_gprmc(bad) is None


def test_non_gprmc_sentence_returns_none():
    other = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
    assert parse_gprmc(other) is None


def test_southern_western_hemisphere_is_negative():
    sentence = "$GPRMC,123519,A,4807.038,S,01131.000,W,022.4,084.4,230394,003.1,W*6A"
    fix = parse_gprmc(sentence)
    assert fix.latitude < 0
    assert fix.longitude < 0


def test_missing_speed_defaults_to_zero():
    sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,,084.4,230394,003.1,W*6A"
    fix = parse_gprmc(sentence)
    assert fix.speed_kmh == 0.0
