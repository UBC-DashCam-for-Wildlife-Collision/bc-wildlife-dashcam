"""Highest-risk-only alert selection for multi-detection frames.

Per docs/meeting_log.md (supervisor direction): when several objects are
detected in one frame, only alert on the highest-risk class. Every detection
is still logged regardless -- this module only decides what to *alert* on.
"""

from dataclasses import dataclass

from src.config import SpeciesTable


@dataclass(frozen=True)
class Detection:
    track_id: int
    label: str
    confidence: float
    distance_m: float


def select_alert_detection(detections: list[Detection], species_table: SpeciesTable) -> Detection | None:
    """Pick the single detection to alert on: highest risk tier, then closest.

    Returns None for an empty list (nothing to alert on, still fine to log
    nothing since there's nothing to log).
    """
    if not detections:
        return None

    def sort_key(d: Detection) -> tuple[int, float]:
        species = species_table.species.get(d.label)
        rank = species_table.risk_rank(species.risk_tier) if species else len(species_table.risk_priority)
        return (rank, d.distance_m)  # lower rank = higher risk; then nearer wins

    return min(detections, key=sort_key)
