"""Geometric handshape predicates (fist / S / A) over a single hand's 21 landmarks.

Pure 2D geometry, orientation-tolerant where possible. Each predicate returns a confidence in
[0, 1]. The verifier smooths these across recent frames (median) so one noisy frame can't flip a
result. Thresholds here are a tuned-by-eye first pass — the Phase 3 live demo exists to calibrate
them on real hands.

Minimal-pair note: A vs S vs a plain fist are all "four fingers curled"; they differ only by the
thumb. v1 treats "fist"/"S" as four-fingers-curled (thumb unconstrained) and "A" as
four-fingers-curled PLUS thumb extended alongside.
"""
from __future__ import annotations

import numpy as np

from core.landmarks import (
    Hand,
    WRIST,
    THUMB_TIP,
    INDEX_MCP,
    INDEX_TIP,
    MIDDLE_MCP,
    MIDDLE_TIP,
    RING_MCP,
    RING_TIP,
    PINKY_MCP,
    PINKY_TIP,
)

# (tip, mcp) for the four non-thumb fingers
_FINGERS = (
    (INDEX_TIP, INDEX_MCP),
    (MIDDLE_TIP, MIDDLE_MCP),
    (RING_TIP, RING_MCP),
    (PINKY_TIP, PINKY_MCP),
)


def _xy(hand: Hand, idx: int) -> np.ndarray:
    return hand.points[idx, :2]


def _hand_scale(hand: Hand) -> float:
    """Stable within-hand length: wrist -> middle-finger MCP."""
    s = float(np.linalg.norm(_xy(hand, MIDDLE_MCP) - _xy(hand, WRIST)))
    return s if s > 1e-6 else 1.0


def _finger_curl(hand: Hand, tip: int, mcp: int) -> float:
    """1.0 = curled (tip folded toward the palm), 0.0 = extended.

    Uses the ratio of (tip->wrist) to (mcp->wrist): an extended finger puts its tip far past the
    knuckle from the wrist (ratio ~1.6+); a curled finger folds the tip back toward the palm so
    the ratio drops to ~1.0 or below.
    """
    tip_d = float(np.linalg.norm(_xy(hand, tip) - _xy(hand, WRIST)))
    mcp_d = float(np.linalg.norm(_xy(hand, mcp) - _xy(hand, WRIST)))
    r = tip_d / max(mcp_d, 1e-6)
    return float(np.clip((1.6 - r) / (1.6 - 1.0), 0.0, 1.0))


def _thumb_extended(hand: Hand) -> float:
    """1.0 = thumb sticking out alongside the hand, 0.0 = tucked/across the palm."""
    d = float(np.linalg.norm(_xy(hand, THUMB_TIP) - _xy(hand, INDEX_MCP))) / _hand_scale(hand)
    return float(np.clip((d - 0.5) / (1.2 - 0.5), 0.0, 1.0))


def fist_confidence(hand: Hand) -> float:
    """Four fingers curled (thumb unconstrained). Covers fist and the S-handshape."""
    return float(np.mean([_finger_curl(hand, t, m) for t, m in _FINGERS]))


def a_confidence(hand: Hand) -> float:
    """Letter A: four fingers curled AND thumb extended alongside."""
    return float(min(fist_confidence(hand), _thumb_extended(hand)))


_DISPATCH = {
    "fist": fist_confidence,
    "s": fist_confidence,
    "a": a_confidence,
}


def handshape_confidence(hand: Hand, kind: str) -> float:
    """Confidence in [0,1] that `hand` forms handshape `kind`. Unknown kinds score 0."""
    fn = _DISPATCH.get(kind.lower())
    return fn(hand) if fn is not None else 0.0
