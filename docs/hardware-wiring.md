# Hardware Wiring — LED bar, OLED, Buzzer

Physical wiring reference for the three alert-output peripherals. Power off
the Pi before wiring anything. Connect GND first, disconnect power last.

Pin numbers below are **physical header pin numbers** (the 1-40 count on the
board), not BCM GPIO numbers, except where noted.

---

## SSD1306 OLED (I2C)

| OLED pin | Connects to | Pi 5 physical pin |
|---|---|---|
| VCC | 3.3V | Pin 1 |
| GND | GND | Pin 6 (any GND works) |
| SCL | GPIO3 / SCL | Pin 5 |
| SDA | GPIO2 / SDA | Pin 3 |

I2C must be enabled and the Pi rebooted before the display will respond:
```
sudo raspi-config nonint do_i2c 0
sudo reboot
```
After reboot, confirm the display shows up on the bus (expected address `0x3C`):
```
i2cdetect -y 1
```
Driver: `src/alerts/oled_display.py`. Test script: `scripts/test_oled.py`.

---

## WS2812B LED bar

Data line on **GPIO18** (BCM numbering — matches `GPIO_PIN` in
`src/alerts/led_bar.py`).

| LED bar pin | Connects to | Pi 5 physical pin |
|---|---|---|
| GND | GND | Pin 6 (any GND works) |
| VCC / 5V | 5V | Pin 2 or 4 |
| DIN (data) | GPIO18 | Pin 12 |

A 300–500Ω resistor inline on the DIN wire is good practice but not required
for a short bench test.

Driver: `src/alerts/led_bar.py`. Test script: `scripts/test_led_bar.py`.
Expected patterns (per `config/alert-zones.yaml`): amber pulse (0.3s cycle,
zone 2), red flash (0.1s cycle, zone 3).

---

## Piezo buzzer

**Pin not yet confirmed.** `src/alerts/buzzer.py` currently uses `GPIO17` as
a placeholder — this was never nailed down against real wiring (unlike the
LED bar and the GPS UART pin, which are fixed in `interface_contract.md`).
Wire it to GPIO17 to match the placeholder, or wire it wherever is
convenient and then update `BUZZER_PIN` in `src/alerts/buzzer.py` to match —
just make sure the two agree before running `scripts/test_buzzer.py`.

**If it's a 3-pin active buzzer module** (labeled VCC / GND / I/O or S):
- VCC → 3.3V or 5V per the module's label
- GND → GND
- I/O → GPIO17 (or your chosen pin)

**If it's a bare 2-pin piezo** (no board):
- `+` → GPIO17 (or your chosen pin)
- `−` → GND directly, no resistor needed at this current draw

Driver: `src/alerts/buzzer.py`. Test script: `scripts/test_buzzer.py`.
Expected patterns (per `config/alert-zones.yaml`): two short beeps (zone 2),
continuous rapid beep (zone 3).

---

## Verification order

1. OLED first — simplest, and confirms I2C is alive.
2. LED bar — confirms the Pi5-specific neopixel/blinka driver path works
   (`requirements-pi.txt`; classic `rpi_ws281x` does not work on the Pi 5's
   RP1 I/O chip).
3. Buzzer — confirm the pin in `src/alerts/buzzer.py` matches how it was
   actually wired before testing.

Run each test script and confirm real physical output (text on the OLED,
visible LED patterns, audible buzzer patterns) — not just a clean exit.
