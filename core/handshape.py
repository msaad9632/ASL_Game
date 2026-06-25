"""Geometric handshape predicates — pure landmark math, no ML.

Each predicate takes a Hand (21 landmarks) and returns a confidence in [0, 1]. The classifiers
are deliberately coarse: they bucket a hand into the handful of shapes the hospital v1 signs need
(A, fist/S, index, open, claw). A vs S/fist is a minimal pair distinguished only by thumb
position; the thumb check below handles that split (imperfectly, as expected for rule-based v1).

Smoothing across frames is done by the verifier (it averages per-frame scores over the buffer),
so a single noisy frame cannot flip a verdict.
"""
from __future__ import annotations

import numpy as np

from core.landmarks import (
    Hand,
    WRIST,
    THUMB_TIP,
    INDEX_MCP, INDEX_TIP,
    MIDDLE_TIP, MIDDLE_MCP,
    RING_TIP, RING_MCP,
    PINKY_TIP, PINKY_MCP,
)


# ---------------------------------------------------------------------------
# Low-level geometric helpers
# ---------------------------------------------------------------------------

def _curl(hand: Hand, tip_idx: int, mcp_idx: int) -> float:
    """How curled one finger is: 0 = fully extended, 1 = fully curled toward the palm.

    Proxy: compare the tip's distance from the wrist to the MCP's distance from the wrist.
    Extended fingers put the tip far past the MCP; a curled finger brings the tip back in.
    """
    pts = hand.points
    wrist = pts[WRIST, :2]
    d_tip = float(np.linalg.norm(pts[tip_idx, :2] - wrist))
    d_mcp = float(np.linalg.norm(pts[mcp_idx, :2] - wrist))
    if d_mcp < 1e-6:
        return 0.0
    return float(np.clip(1.0 - (d_tip - d_mcp) / d_mcp, 0.0, 1.0))


def _finger_curls(hand: Hand) -> np.ndarray:
    """Curl values for [index, middle, ring, pinky], each in [0, 1]."""
    pairs = [(INDEX_TIP, INDEX_MCP), (MIDDLE_TIP, MIDDLE_MCP),
             (RING_TIP, RING_MCP), (PINKY_TIP, PINKY_MCP)]
    return np.array([_curl(hand, t, m) for t, m in pairs])


def _thumb_out(hand: Hand) -> float:
    """How far the thumb sits from the index MCP (0 = tucked/wrapped, 1 = out/up alongside)."""
    pts = hand.points
    d = float(np.linalg.norm(pts[THUMB_TIP, :2] - pts[INDEX_MCP, :2]))
    scale = float(np.linalg.norm(pts[INDEX_MCP, :2] - pts[WRIST, :2])) + 1e-6
    return float(np.clip(d / scale, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Public classifiers — each returns a confidence in [0, 1]
# ---------------------------------------------------------------------------

def is_fist(hand: Hand) -> float:
    """S-hand / plain fist: four fingers curled, thumb wrapped across (tucked in)."""
    curls = _finger_curls(hand)
    fingers_curled = float(np.mean(curls))
    thumb_tucked = 1.0 - _thumb_out(hand)
    return float(np.clip(fingers_curled * 0.7 + thumb_tucked * 0.3, 0.0, 1.0))


def is_A(hand: Hand) -> float:
    """A-hand: closed fist, but the thumb sits alongside / up (not wrapped across)."""
    curls = _finger_curls(hand)
    fingers_curled = float(np.mean(curls))
    thumb_up = _thumb_out(hand)
    return float(np.clip(fingers_curled * 0.65 + thumb_up * 0.35, 0.0, 1.0))


def is_index(hand: Hand) -> float:
    """Index finger extended, the other three curled (1-hand / D / pointing)."""
    curls = _finger_curls(hand)
    index_extended = 1.0 - curls[0]
    rest_curled = float(np.mean(curls[1:]))
    return float(np.clip(index_extended * 0.5 + rest_curled * 0.5, 0.0, 1.0))


def is_open(hand: Hand) -> float:
    """Open / flat hand: all four fingers extended (B-hand / flat palm / 5)."""
    curls = _finger_curls(hand)
    return float(np.clip(1.0 - float(np.mean(curls)), 0.0, 1.0))


def is_claw(hand: Hand) -> float:
    """Claw: fingers clearly curled (approximates E-hand / bent-5 / closed-ish hand).

    Used for MEDICINE (dominant) and EMERGENCY. No hospital sign needs to distinguish a claw from a
    plain fist, so this is deliberately generous: any hand whose fingers are meaningfully curled
    (not flat, not pointing) scores high. The defining feature for these two signs is the MOTION
    (repeated twist / rapid shake), which the verifier gates separately — the handshape only has to
    confirm the hand is closed-ish, not flat or pointing.
    """
    curls = _finger_curls(hand)
    m = float(np.mean(curls))
    return float(np.clip((m - 0.25) / 0.35, 0.0, 1.0))  # 0 at flat (~0.25), saturates by ~0.60


# ---------------------------------------------------------------------------
# Dispatch by the kind strings used in core/schema.py (HandShapeReq.kind)
# ---------------------------------------------------------------------------

_CLASSIFIERS = {
    "fist": is_fist,
    "A": is_A,
    "index": is_index,
    "open": is_open,
    "claw": is_claw,
}


def score(hand: Hand, kind: str) -> float:
    """Confidence in [0, 1] that `hand` is making handshape `kind`."""
    fn = _CLASSIFIERS.get(kind)
    if fn is None:
        raise ValueError(f"Unknown handshape kind '{kind}' — add a classifier in core/handshape.py.")
    return fn(hand)
