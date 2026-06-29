"""Phase 2 — Handshape preset library (the inverse of core.handshape).

The recognition side (`core.handshape`) reads 21 hand landmarks and scores how well they form a
named handshape. The synthesis side does the opposite: given a handshape NAME, it deterministically
*produces* a canonical set of 21 landmarks that the recognition predicates score highly. This is a
finite, one-time data task — exactly the "discrete data-lookup" the procedural-avatar report calls
for (Phase 2): the system never re-derives a handshape dynamically, it looks one up.

Because `core.handshape`'s predicates are built from rotation/translation-invariant distance ratios
(tip-vs-knuckle reach, thumb spread relative to hand scale), a preset only needs the right *radial*
finger geometry — it works regardless of where the arm later carries the hand in the frame. Phase 5
(`core.synthesis`) translates and orients these local poses into body-relative position.

Topology is the standard MediaPipe 21-point hand (see core.landmarks): wrist, then thumb
(cmc/mcp/ip/tip) and four fingers (mcp/pip/dip/tip). Local coordinates put the wrist at the origin
with the fingers pointing "up" the image (toward -y) and the palm toward the camera; z stays 0 so a
well-defined palm normal points at the camera.

Each entry of SHAPE_SPECS is (per-finger extension in [0,1] for index/middle/ring/pinky,
thumb_extended bool). 1.0 = fully extended, 0.0 = fully curled; intermediate values (the claw) sit
partway. These specs are the single source of truth shared by every sign that reuses the shape.
"""
from __future__ import annotations

import numpy as np

# Local hand scale (px): the wrist->middle-knuckle distance. Synthesis may rescale per avatar size.
CANON_SCALE = 60.0

# Knuckle (MCP) positions as multiples of CANON_SCALE, fingers pointing up (-y). middle_mcp sits at
# ~1.0 scale from the wrist so it defines the hand scale the predicates normalize against.
_MCP = {
    "index": np.array([-0.35, -0.95]),
    "middle": np.array([-0.10, -1.00]),
    "ring": np.array([0.15, -0.95]),
    "pinky": np.array([0.38, -0.82]),
}
_FINGER_ORDER = ("index", "middle", "ring", "pinky")

# Radial reach of pip/dip/tip as multiples of the knuckle distance |mcp|. An extended finger throws
# its tip well past the knuckle (ratio ~1.8 -> reads "extended"); a curled finger folds the tip back
# inside the knuckle (ratio ~0.80 -> reads "curled"). Intermediate extension lerps between the two.
# Curled chain stays monotonically inside the knuckle (no spike past the MCP) so a fist reads as a
# rounded fist rather than splayed spikes; extended throws the tip well past the knuckle.
_CHAIN_CURLED = np.array([0.95, 0.82, 0.74])
_CHAIN_EXTENDED = np.array([1.30, 1.58, 1.82])

# Thumb tip positions (in scale units): extended thumb juts away from the index knuckle (large spread
# relative to hand scale -> reads "extended"); tucked thumb crosses toward the palm (small spread).
_THUMB_CMC = np.array([-0.25, -0.20])
_THUMB_TIP_OUT = np.array([-1.25, -0.25])
_THUMB_TIP_TUCKED = np.array([0.00, -0.62])

# (index, middle, ring, pinky) extension, thumb_extended. Aliases share one spec so a sign asking for
# "s" and one asking for "fist" animate identically — the same reuse the recognition dispatch relies on.
SHAPE_SPECS: dict[str, tuple[tuple[float, float, float, float], float]] = {
    "fist":   ((0.0, 0.0, 0.0, 0.0), 0.0),    # fully folded thumb
    "s":      ((0.0, 0.0, 0.0, 0.0), 0.0),    # fully folded thumb
    "a":      ((0.0, 0.0, 0.0, 0.0), 0.5),    # thumb alongside index, not fully folded
    "open":   ((1.0, 1.0, 1.0, 1.0), 1.0),
    "b":      ((1.0, 1.0, 1.0, 1.0), 0.3),    # thumb tucked across palm
    "5":      ((1.0, 1.0, 1.0, 1.0), 1.0),
    "claw":   ((0.40, 0.40, 0.40, 0.40), 1.0),
    "index":  ((1.0, 0.0, 0.0, 0.0), 0.0),
    "point":  ((1.0, 0.0, 0.0, 0.0), 0.0),
    "1":      ((1.0, 0.0, 0.0, 0.0), 0.0),
    "v":      ((1.0, 1.0, 0.0, 0.0), 0.0),
    "l":      ((1.0, 0.0, 0.0, 0.0), 1.0),    # index + thumb extended
    "y":      ((0.0, 0.0, 0.0, 1.0), 1.0),    # pinky + thumb extended
    "n":      ((1.0, 1.0, 0.0, 0.0), 0.0),
    "h":      ((1.0, 1.0, 0.0, 0.0), 0.0),
    "u":      ((1.0, 1.0, 0.0, 0.0), 0.0),
    "w":      ((1.0, 1.0, 1.0, 0.0), 0.0),
    "middle": ((0.0, 1.0, 0.0, 0.0), 0.0),
}


def supported_shapes() -> list[str]:
    return sorted(SHAPE_SPECS.keys())


def _finger_chain(name: str, extension: float) -> np.ndarray:
    """pip, dip, tip (3 points, 2D) for one finger at the given extension in [0, 1]."""
    mcp = _MCP[name]
    reach = np.linalg.norm(mcp)
    unit = mcp / reach
    mults = _CHAIN_CURLED + (_CHAIN_EXTENDED - _CHAIN_CURLED) * float(np.clip(extension, 0.0, 1.0))
    return np.array([unit * (m * reach) for m in mults])


def _thumb_chain(extension: float) -> np.ndarray:
    """thumb mcp, ip, tip (3 points, 2D). cmc is fixed; the rest lerp between tucked and out."""
    ext = float(extension) if not isinstance(extension, bool) else (1.0 if extension else 0.0)
    tip = _THUMB_TIP_TUCKED + (_THUMB_TIP_OUT - _THUMB_TIP_TUCKED) * ext
    return np.array([_THUMB_CMC + (tip - _THUMB_CMC) * f for f in (0.40, 0.72, 1.0)])


def local_hand(kind: str, scale: float = CANON_SCALE, mirror: bool = False) -> np.ndarray:
    """Canonical 21x3 landmark array for a handshape, wrist at origin, in pixel units.

    `mirror` flips x (a left/right hand pair facing each other) — purely cosmetic for rendering;
    every recognition predicate is mirror-invariant. Raises KeyError for an unsupported kind so a
    typo in a sign definition fails loudly rather than silently animating an empty hand.
    """
    key = kind.lower()
    if key not in SHAPE_SPECS:
        raise KeyError(
            f"No handshape preset for '{kind}'. Known: {', '.join(supported_shapes())}"
        )
    extensions, thumb_out = SHAPE_SPECS[key]

    pts = np.zeros((21, 3), dtype=float)        # index 0 = wrist = origin
    mcp_t, ip_t, tip_t = _thumb_chain(thumb_out)
    pts[1, :2] = _THUMB_CMC                       # thumb cmc
    pts[2, :2], pts[3, :2], pts[4, :2] = mcp_t, ip_t, tip_t   # mcp, ip, tip

    base = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}
    for name, e in zip(_FINGER_ORDER, extensions):
        i = base[name]
        pts[i, :2] = _MCP[name]                  # mcp
        chain = _finger_chain(name, e)           # pip, dip, tip
        pts[i + 1, :2], pts[i + 2, :2], pts[i + 3, :2] = chain

    pts[:, :2] *= scale
    if mirror:
        pts[:, 0] *= -1.0
    return pts
