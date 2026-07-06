"""Distance estimation: thin-lens (P1) and time-to-contact optical expansion (P2).

Thin-lens needs the camera's focal length in pixels, which comes from
Aditya's checkerboard calibration (`camera_matrix.npy`, per
docs/interface_contract.md section 2). That file does not exist yet, so
`focal_length_px` is a required argument here rather than a hardcoded
constant -- wire it up to the real calibration value as soon as it lands.
"""

from dataclasses import dataclass

from src.config import SpeciesConfig


def thin_lens_distance_m(bbox_height_px: float, shoulder_height_m: float, focal_length_px: float) -> float:
    """Estimate distance from apparent object size (thin-lens / pinhole model).

    distance = (real_height * focal_length) / apparent_height_px
    """
    if bbox_height_px <= 0:
        raise ValueError("bbox_height_px must be positive")
    return (shoulder_height_m * focal_length_px) / bbox_height_px


def thin_lens_distance_for_species(bbox_height_px: float, species: SpeciesConfig, focal_length_px: float) -> float:
    return thin_lens_distance_m(bbox_height_px, species.shoulder_height_m, focal_length_px)


@dataclass(frozen=True)
class BBoxSample:
    """A single frame's observation of one tracked object, for TTC estimation."""

    timestamp_s: float
    bbox_height_px: float


def ttc_distance_m(previous: BBoxSample, current: BBoxSample, vehicle_speed_mps: float) -> float | None:
    """Time-to-contact via optical expansion, converted to a distance estimate.

    TTC = time / (1 - height_ratio) is the standard looming/expansion formula
    (Lee 1976 tau). We convert the resulting time-to-contact into a distance
    using the vehicle's current speed. Returns None when the bbox is not
    growing (object not approaching, or too little motion to measure) --
    callers should fall back to thin-lens distance in that case.
    """
    dt = current.timestamp_s - previous.timestamp_s
    if dt <= 0:
        return None
    height_ratio = previous.bbox_height_px / current.bbox_height_px
    if height_ratio >= 1.0:
        # Bbox shrank or stayed flat: object is not approaching (or noise).
        return None
    ttc_s = dt / (1.0 - height_ratio)
    if ttc_s <= 0 or vehicle_speed_mps <= 0:
        return None
    return ttc_s * vehicle_speed_mps


def fused_distance_m(thin_lens_m: float, ttc_m: float | None) -> float:
    """Conservative fusion: d_final = min(d_ttc, d_thin_lens) per CLAUDE.md section 6.

    Taking the minimum means whichever method reports the more dangerous
    (closer) distance wins, biasing toward earlier alerts rather than
    missed ones.
    """
    if ttc_m is None:
        return thin_lens_m
    return min(thin_lens_m, ttc_m)
