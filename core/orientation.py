"""Palm-orientation estimate from hand landmarks.

Rough first pass: derive a palm normal from wrist + index-MCP + pinky-MCP (3D) and score how
well it aligns with a requested facing. Only enforced when a sign marks orientation required
(none of the v1 signs do), so this is intentionally lightweight.
"""
from __future__ import annotations

import numpy as np

from core.landmarks import Hand, WRIST, INDEX_MCP, PINKY_MCP
from core.schema import PalmFacing

# image-space axis convention: x right, y down, z toward camera (MediaPipe-ish)
_TARGETS = {
    PalmFacing.DOWN: (0.0, 1.0, 0.0),
    PalmFacing.UP: (0.0, -1.0, 0.0),
    PalmFacing.RIGHT: (1.0, 0.0, 0.0),
    PalmFacing.LEFT: (-1.0, 0.0, 0.0),
    PalmFacing.IN: (0.0, 0.0, 1.0),
    PalmFacing.OUT: (0.0, 0.0, -1.0),
}


def palm_normal(hand: Hand) -> np.ndarray:
    w = hand.points[WRIST]
    i = hand.points[INDEX_MCP]
    p = hand.points[PINKY_MCP]
    n = np.cross(i - w, p - w)
    norm = float(np.linalg.norm(n))
    return n / norm if norm > 1e-6 else n


def facing_confidence(hand: Hand, facing: PalmFacing) -> float:
    """1.0 = palm normal aligned with the requested facing, 0.0 = orthogonal/opposite."""
    n = palm_normal(hand)
    t = np.asarray(_TARGETS[facing], dtype=float)
    return float(np.clip(float(np.dot(n, t)), 0.0, 1.0))
