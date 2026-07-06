"""Ties a ZoneConfig (config/alert-zones.yaml) to the three alert outputs.

This is the single place that decides "given this zone, do what" -- the
zone-to-pattern mapping lives in config/alert-zones.yaml, not hardcoded here.
"""

from src.alerts.buzzer import Buzzer
from src.alerts.led_bar import LedBar
from src.alerts.oled_display import OledDisplay
from src.config import ZoneConfig


class AlertController:
    def __init__(self, led: LedBar, buzzer: Buzzer, oled: OledDisplay):
        self.led = led
        self.buzzer = buzzer
        self.oled = oled

    def trigger(self, zone: ZoneConfig, species: str | None = None, distance_m: float | None = None) -> None:
        """Fire whatever outputs this zone's config specifies. No-ops for fields left unset."""
        if zone.led is not None:
            if zone.led.pattern == "pulse":
                self.led.pulse(zone.led.color_rgb, zone.led.cycle_ms)
            elif zone.led.pattern == "flash":
                self.led.flash(zone.led.color_rgb, zone.led.cycle_ms)
        else:
            self.led.off()

        if zone.buzzer is not None:
            if zone.buzzer.pattern == "two-short":
                self.buzzer.two_short()
            elif zone.buzzer.pattern == "continuous-rapid":
                self.buzzer.continuous_rapid()
        else:
            self.buzzer.off()

        if zone.oled is not None and zone.oled.show_species and species is not None and distance_m is not None:
            self.oled.show_species_distance(species, distance_m)
        elif zone.oled is None:
            self.oled.clear()
