from src.alerts.buzzer import Buzzer
from src.alerts.controller import AlertController
from src.alerts.led_bar import LedBar
from src.alerts.oled_display import OledDisplay
from src.config import load_zone_table


def make_controller():
    return AlertController(
        led=LedBar(simulate=True),
        buzzer=Buzzer(simulate=True),
        oled=OledDisplay(simulate=True),
    )


def test_zone1_is_silent():
    table = load_zone_table()
    zone1 = next(z for z in table.zones if z.name == "zone1")
    controller = make_controller()

    controller.trigger(zone1)

    assert controller.led.calls == [("set_all", (0, 0, 0))]
    assert controller.buzzer.calls == [("off",)]
    assert controller.oled.calls == [("clear",)]


def test_zone2_pulses_amber_and_beeps_twice():
    table = load_zone_table()
    zone2 = next(z for z in table.zones if z.name == "zone2")
    controller = make_controller()

    controller.trigger(zone2)

    assert controller.led.calls == [("pulse", (255, 180, 0), 300, 3)]
    assert controller.buzzer.calls == [("two_short", 0.15, 0.15)]


def test_zone3_flashes_red_beeps_rapid_and_shows_oled():
    table = load_zone_table()
    zone3 = next(z for z in table.zones if z.name == "zone3")
    controller = make_controller()

    controller.trigger(zone3, species="moose", distance_m=15.0)

    assert controller.led.calls == [("flash", (255, 0, 0), 100, 5)]
    assert controller.buzzer.calls == [("continuous_rapid", 1.0, 0.08, 0.05)]
    assert controller.oled.calls == [("show_species_distance", "moose", 15.0)]
