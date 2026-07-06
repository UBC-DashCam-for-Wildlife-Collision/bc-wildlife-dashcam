"""Approach-vector filter: only alert on objects moving toward the car.

Per docs/meeting_log.md (supervisor direction): a shrinking bounding box
means the animal is retreating -- no alert, though the detection is still
logged. Tracking is done upstream by the Hailo tracker (per-object track ID);
this module just keeps a short bbox-height history per track and classifies
the trend.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class ApproachState(Enum):
    APPROACHING = "approaching"
    RETREATING = "retreating"
    UNKNOWN = "unknown"  # not enough history yet


@dataclass
class TrackHistory:
    track_id: int
    heights_px: deque[float] = field(default_factory=lambda: deque(maxlen=5))

    def update(self, bbox_height_px: float) -> None:
        self.heights_px.append(bbox_height_px)

    def state(self, noise_margin: float = 0.02) -> ApproachState:
        """Compare oldest vs newest height in the window.

        noise_margin is a fractional threshold (default 2%) so that
        jitter-sized fluctuations between consecutive frames don't flip the
        state back and forth.
        """
        if len(self.heights_px) < 2:
            return ApproachState.UNKNOWN
        first, last = self.heights_px[0], self.heights_px[-1]
        if first <= 0:
            return ApproachState.UNKNOWN
        change = (last - first) / first
        if change > noise_margin:
            return ApproachState.APPROACHING
        if change < -noise_margin:
            return ApproachState.RETREATING
        return ApproachState.UNKNOWN


class ApproachTracker:
    """Keeps per-track bbox-height history across frames and reports state."""

    def __init__(self, window: int = 5, noise_margin: float = 0.02):
        self._window = window
        self._noise_margin = noise_margin
        self._tracks: dict[int, TrackHistory] = {}

    def observe(self, track_id: int, bbox_height_px: float) -> ApproachState:
        history = self._tracks.get(track_id)
        if history is None:
            history = TrackHistory(track_id=track_id, heights_px=deque(maxlen=self._window))
            self._tracks[track_id] = history
        history.update(bbox_height_px)
        return history.state(self._noise_margin)

    def should_alert(self, track_id: int, bbox_height_px: float) -> bool:
        """True unless the track is confidently retreating."""
        return self.observe(track_id, bbox_height_px) != ApproachState.RETREATING

    def forget(self, track_id: int) -> None:
        """Drop history for a track that's left the frame (tracker recycles IDs)."""
        self._tracks.pop(track_id, None)
