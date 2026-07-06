"""Typed loaders for config/species.yaml and config/alert-zones.yaml."""

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


@dataclass(frozen=True)
class SpeciesConfig:
    label: str
    taxon: str
    shoulder_height_m: float
    risk_tier: str


@dataclass(frozen=True)
class SpeciesTable:
    species: dict[str, SpeciesConfig]
    risk_priority: list[str]

    def risk_rank(self, risk_tier: str) -> int:
        """Lower rank = higher priority. Unknown tiers sort last."""
        try:
            return self.risk_priority.index(risk_tier)
        except ValueError:
            return len(self.risk_priority)


@dataclass(frozen=True)
class LedConfig:
    color_rgb: tuple[int, int, int]
    pattern: str
    cycle_ms: int


@dataclass(frozen=True)
class BuzzerConfig:
    pattern: str


@dataclass(frozen=True)
class OledConfig:
    show_species: bool
    show_distance: bool


@dataclass(frozen=True)
class ZoneConfig:
    name: str
    label: str
    min_distance_m: float
    led: LedConfig | None
    buzzer: BuzzerConfig | None
    oled: OledConfig | None


@dataclass(frozen=True)
class ZoneTable:
    zones: list[ZoneConfig]  # ordered widest-range (zone1) to narrowest (zone3)

    def zone_for_distance(self, distance_m: float) -> ZoneConfig:
        """Highest-numbered zone whose min_distance_m the given distance satisfies.

        Zones are checked narrowest-first so a distance inside multiple
        overlapping thresholds resolves to the more urgent zone.
        """
        candidates = sorted(self.zones, key=lambda z: z.min_distance_m, reverse=True)
        for zone in candidates:
            if distance_m >= zone.min_distance_m:
                return zone
        return candidates[-1]


def load_species_table(path: Path | None = None) -> SpeciesTable:
    path = path or CONFIG_DIR / "species.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    species = {
        entry["label"]: SpeciesConfig(
            label=entry["label"],
            taxon=entry["taxon"],
            shoulder_height_m=float(entry["shoulder_height_m"]),
            risk_tier=entry["risk_tier"],
        )
        for entry in raw["classes"]
    }
    return SpeciesTable(species=species, risk_priority=list(raw["risk_priority"]))


def _load_led(raw: dict | str | None) -> LedConfig | None:
    if not isinstance(raw, dict):
        return None
    r, g, b = raw["color_rgb"]
    return LedConfig(color_rgb=(int(r), int(g), int(b)), pattern=raw["pattern"], cycle_ms=int(raw["cycle_ms"]))


def _load_buzzer(raw: dict | str | None) -> BuzzerConfig | None:
    if not isinstance(raw, dict):
        return None
    return BuzzerConfig(pattern=raw["pattern"])


def _load_oled(raw: dict | str | None) -> OledConfig | None:
    if not isinstance(raw, dict):
        return None
    return OledConfig(show_species=bool(raw.get("show_species", False)), show_distance=bool(raw.get("show_distance", False)))


def load_zone_table(path: Path | None = None) -> ZoneTable:
    path = path or CONFIG_DIR / "alert-zones.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    zones = [
        ZoneConfig(
            name=name,
            label=entry["label"],
            min_distance_m=float(entry["min_distance_m"]),
            led=_load_led(entry.get("led")),
            buzzer=_load_buzzer(entry.get("buzzer")),
            oled=_load_oled(entry.get("oled")),
        )
        for name, entry in raw["zones"].items()
    ]
    return ZoneTable(zones=zones)
