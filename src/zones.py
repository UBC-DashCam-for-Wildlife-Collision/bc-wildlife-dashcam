"""Proximity-zone classification, per config/alert-zones.yaml thresholds."""

from src.config import ZoneConfig, ZoneTable


def speed_scale_factor(speed_kmh: float) -> float:
    """Scales zone thresholds outward at higher speed (P2, CLAUDE.md section 6).

    Not yet calibrated -- returns 1.0 (no scaling) until real road-test data
    justifies a curve. Kept as a separate function so `classify_zone` doesn't
    need to change shape when this gets a real implementation.
    """
    return 1.0


def classify_zone(distance_m: float, zone_table: ZoneTable, speed_kmh: float = 0.0) -> ZoneConfig:
    """Map a distance estimate to a zone, optionally speed-scaled."""
    scale = speed_scale_factor(speed_kmh)
    if scale == 1.0:
        return zone_table.zone_for_distance(distance_m)

    scaled_zones = [
        ZoneConfig(
            name=z.name,
            label=z.label,
            min_distance_m=z.min_distance_m * scale,
            led=z.led,
            buzzer=z.buzzer,
            oled=z.oled,
        )
        for z in zone_table.zones
    ]
    return ZoneTable(zones=scaled_zones).zone_for_distance(distance_m)
