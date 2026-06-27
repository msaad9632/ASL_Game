"""Geometric handshape predicates over a single hand's 21 landmarks.

Pure 2D geometry, orientation-tolerant where possible. Each predicate returns a confidence in
[0, 1]. The verifier smooths these across recent frames (median) so one noisy frame can't flip a
result.

Shapes supported:
  fist / s — four fingers curled, thumb unconstrained (S-hand / plain fist)
  a         — four fingers curled AND thumb extended alongside (letter A)
  index     — index extended, other three curled (pointing / "1" hand)
  open      — all four fingers extended (flat palm / B-hand)
  claw      — fingers clearly curled but not fully closed (E-hand / bent-5)

Minimal-pair note: A vs S vs plain fist are all "four fingers curled"; they differ only by thumb
position. index vs open differ by how many fingers are extended.
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
    """1.0 = curled (tip folded toward palm), 0.0 = extended.

    Uses the ratio of (tip->wrist) to (mcp->wrist): an extended finger puts its tip far past the
    knuckle (ratio ~1.6+); a curled finger folds the tip back (ratio drops to ~1.0 or below).
    Calibrated on real hands in Phase 3.
    """
    tip_d = float(np.linalg.norm(_xy(hand, tip) - _xy(hand, WRIST)))
    mcp_d = float(np.linalg.norm(_xy(hand, mcp) - _xy(hand, WRIST)))
    r = tip_d / max(mcp_d, 1e-6)
    return float(np.clip((1.6 - r) / (1.6 - 1.0), 0.0, 1.0))


def _all_curls(hand: Hand) -> list[float]:
    return [_finger_curl(hand, t, m) for t, m in _FINGERS]


def _thumb_extended(hand: Hand) -> float:
    """1.0 = thumb sticking out alongside the hand, 0.0 = tucked/across the palm."""
    d = float(np.linalg.norm(_xy(hand, THUMB_TIP) - _xy(hand, INDEX_MCP))) / _hand_scale(hand)
    return float(np.clip((d - 0.5) / (1.2 - 0.5), 0.0, 1.0))


# ---------------------------------------------------------------------------
# Public classifiers
# ---------------------------------------------------------------------------

def fist_confidence(hand: Hand) -> float:
    """Four fingers curled (thumb unconstrained). Covers fist and S-handshape."""
    return float(np.mean(_all_curls(hand)))


def a_confidence(hand: Hand) -> float:
    """Letter A: four fingers curled AND thumb extended alongside (not wrapped across)."""
    return float(min(fist_confidence(hand), _thumb_extended(hand)))


def index_confidence(hand: Hand) -> float:
    """Index finger extended, the other three curled (1-hand / D / pointing)."""
    curls = _all_curls(hand)
    index_extended = 1.0 - curls[0]
    rest_curled = float(np.mean(curls[1:]))
    return float(np.clip(index_extended * 0.5 + rest_curled * 0.5, 0.0, 1.0))


def open_confidence(hand: Hand) -> float:
    """Open / flat hand: all four fingers extended (B-hand / flat palm / 5)."""
    curls = _all_curls(hand)
    return float(np.clip(1.0 - float(np.mean(curls)), 0.0, 1.0))


def claw_confidence(hand: Hand) -> float:
    """Fingers clearly curled but not fully closed (E-hand / bent-5 approximation).

    Used for MEDICINE and EMERGENCY. Generously scored: any meaningfully-curled hand that isn't
    flat or pointing passes. The motion detector (repeated) carries the discriminating weight for
    these two signs; the handshape only needs to confirm the hand is closed-ish.
    """
    curls = _all_curls(hand)
    m = float(np.mean(curls))
    return float(np.clip((m - 0.25) / 0.35, 0.0, 1.0))   # 0 at flat, saturates ~0.60


# ---------------------------------------------------------------------------
# Dispatch — matches the `kind` strings used in HandShapeReq
# ---------------------------------------------------------------------------

_DISPATCH = {
    "fist": fist_confidence,
    "s": fist_confidence,
    "a": a_confidence,
    "index": index_confidence,
    "open": open_confidence,
    "b": open_confidence,           # Saad's PLEASE/THANK_YOU use "b" / "5" — same shape as open
    "5": open_confidence,
    "claw": claw_confidence,
}


def handshape_confidence(hand: Hand, kind: str) -> float:
    """Confidence in [0, 1] that `hand` forms handshape `kind`. Unknown kinds score 0."""
    fn = _DISPATCH.get(kind.lower())
    return fn(hand) if fn is not None else 0.0
