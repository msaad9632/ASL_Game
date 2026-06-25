"""Palm-orientation estimate from hand landmarks.

A coarse v1 estimate of which way the palm faces, derived from the palm plane (wrist + index MCP
+ pinky MCP). Only the in-image axes (up/down/left/right) are reliable from 2D landmarks; the
toward/away-camera split uses MediaPipe's relative z. Orientation is a schema placeholder in v1 —
it is computed for the debug overlay but only *gated* when a sign sets palm_orientation.required.
"""
from __future__ import annotations

import numpy as np

from core.landmarks import Hand, WRIST, MIDDLE_MCP


def palm_vector(hand: Hand) -> np.ndarray:
    """Unit vector from the wrist toward the middle-finger MCP — the direction the palm points."""
    pts = hand.points
    v = pts[MIDDLE_MCP, :2] - pts[WRIST, :2]
    n = np.linalg.norm(v)
    return v / n if n > 1e-6 else np.array([0.0, -1.0])


def score(hand: Hand, facing: str) -> float:
    """Confidence in [0, 1] that the palm faces `facing` (up/down/left/right) in the image plane.

    'up'/'down' use the palm vector's vertical component (image y grows downward, so up = -y);
    'left'/'right' use its horizontal component. Returns 0.5 (neutral) for unknown facings so an
    ungated orientation never accidentally fails a sign.
    """
    v = palm_vector(hand)
    targets = {
        "up": np.array([0.0, -1.0]),
        "down": np.array([0.0, 1.0]),
        "left": np.array([-1.0, 0.0]),
        "right": np.array([1.0, 0.0]),
    }
    t = targets.get(facing)
    if t is None:
        return 0.5
    # Cosine similarity mapped from [-1,1] to [0,1].
    return float(np.clip((float(np.dot(v, t)) + 1.0) / 2.0, 0.0, 1.0))
