"""Generic temporal verifier — one engine for every sign.

verify(buffer, sign) returns a per-parameter breakdown PLUS an overall pass/fail. The overall
pass requires EVERY parameter marked required to individually clear its own threshold. There is
no averaging: a perfect handshape can never compensate for absent required movement. That gating
is what makes the single-frame COFFEE bug impossible to reproduce.

Role assignment (which detected hand is "dominant"/"nondominant") is a v1 heuristic: the hand
that moved more across the window is the dominant/acting hand, the stiller one is non-dominant.
This is handedness-agnostic and matches signs like COFFEE where one hand acts and one holds
still. (A configurable dominant-hand setting can replace this later.)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core import handshape as hs
from core import movement as mv
from core import orientation as ori
from core.landmarks import RollingBuffer, normalized_distance
from core.schema import DOMINANT, NONDOMINANT, Anchor, MovementKind, Sign

# how much of the most-recent window to smooth handshape/location/orientation over
SMOOTH_SECONDS = 0.5

# Anchor.CHEST geometry, in shoulder-widths below the shoulder line.
# The hand must be at chest HEIGHT: full credit within +-CHEST_VBAND of CHEST_OFFSET_RATIO,
# then a linear falloff over CHEST_VFALL. Tuned so the pass/fail boundary lands at ~dy 0.6:
# chest reads dy <= 0.6 (full credit up to 0.60), belly reads dy > 0.6 and fails.
CHEST_OFFSET_RATIO = 0.35
CHEST_VBAND = 0.25
CHEST_VFALL = 0.12

# Anchor.CHIN: the hand must reach chin height, ~this many shoulder-widths ABOVE the shoulder
# line (negative dy), within CHIN_TOL. Used by signs that START at the chin (e.g. THANK YOU).
CHIN_OFFSET_RATIO = 0.6
CHIN_TOL = 0.5


@dataclass
class ParamScore:
    name: str
    score: float
    threshold: float
    required: bool

    @property
    def cleared(self) -> bool:
        """Did this parameter clear its own threshold (regardless of required)?"""
        return self.score >= self.threshold

    @property
    def passed(self) -> bool:
        """Required params must clear; optional params never block the overall pass."""
        return (not self.required) or self.cleared


@dataclass
class VerifyResult:
    sign_name: str
    params: list[ParamScore]
    roles: dict

    @property
    def passed(self) -> bool:
        required = [p for p in self.params if p.required]
        return len(required) > 0 and all(p.passed for p in required)

    @property
    def failing_required(self) -> list[str]:
        return [p.name for p in self.params if p.required and not p.cleared]

    def get(self, name: str) -> ParamScore | None:
        for p in self.params:
            if p.name == name:
                return p
        return None


# ------------------------------------------------------------------ trajectory helpers
def _trajectory(buffer: RollingBuffer, handedness: str | None):
    if handedness is None:
        return []
    out = []
    for f in buffer:
        h = f.hand(handedness)
        if h is not None:
            out.append((f.t, h.center))
    return out


def _path_length(traj) -> float:
    if len(traj) < 2:
        return 0.0
    pts = np.array([c for _, c in traj], dtype=float)
    return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))


def assign_roles(buffer: RollingBuffer) -> dict:
    """Map DOMINANT/NONDOMINANT to detected handedness labels by relative motion."""
    labels: list[str] = []
    for f in buffer:
        for h in f.hands:
            if h.handedness not in labels:
                labels.append(h.handedness)
    if not labels:
        return {}
    if len(labels) == 1:
        return {DOMINANT: labels[0]}
    labels.sort(key=lambda lab: _path_length(_trajectory(buffer, lab)), reverse=True)
    return {DOMINANT: labels[0], NONDOMINANT: labels[1]}


def _recent(buffer: RollingBuffer, seconds: float):
    frames = list(buffer)
    if not frames:
        return []
    end_t = frames[-1].t
    return [f for f in frames if end_t - f.t <= seconds]


def _latest_shoulder_width(buffer: RollingBuffer):
    for f in reversed(list(buffer)):
        if f.shoulder_width:
            return f.shoulder_width
    return None


# ------------------------------------------------------------------ parameter scorers
def _score_handshape(buffer, handedness, kind) -> float:
    vals = []
    for f in _recent(buffer, SMOOTH_SECONDS):
        h = f.hand(handedness)
        if h is not None:
            vals.append(hs.handshape_confidence(h, kind))
    return float(np.median(vals)) if vals else 0.0


def _score_location(buffer, sign: Sign, roles, shoulder_width) -> float:
    if shoulder_width is None:
        return 0.0
    loc = sign.location
    acting_label = roles.get(loc.acting_hand)
    if acting_label is None:
        return 0.0

    if loc.anchor == Anchor.CHIN:
        return _score_chin_reach(buffer, acting_label, shoulder_width, loc)

    vals = []
    for f in _recent(buffer, SMOOTH_SECONDS):
        acting = f.hand(acting_label)
        if acting is None:
            continue

        if loc.anchor == Anchor.OTHER_HAND:
            other_role = NONDOMINANT if loc.acting_hand == DOMINANT else DOMINANT
            other_label = roles.get(other_role)
            other = f.hand(other_label) if other_label else None
            if other is None:
                continue
            d = normalized_distance(acting.center, other.center, shoulder_width)
            dist_score = _band_score(d, loc.min_dist_ratio, loc.max_dist_ratio)
            vert_score = _vertical_score(loc.vertical, acting.center, other.center, shoulder_width)
            vals.append(min(dist_score, vert_score))
        elif loc.anchor == Anchor.CHEST:
            if f.left_shoulder is None or f.right_shoulder is None:
                continue
            mid = (f.left_shoulder + f.right_shoulder) / 2.0
            dx = abs(acting.center[0] - mid[0]) / shoulder_width      # sideways from center
            dy = (acting.center[1] - mid[1]) / shoulder_width         # below the shoulder line
            v = 1.0 - max(0.0, abs(dy - CHEST_OFFSET_RATIO) - CHEST_VBAND) / CHEST_VFALL
            h = 1.0 - max(0.0, dx - loc.max_dist_ratio) / 0.35
            vals.append(float(np.clip(min(v, h), 0.0, 1.0)))

        else:  # NEUTRAL_SPACE — anywhere in front of the torso, below the shoulders (loose)
            if f.left_shoulder is None or f.right_shoulder is None:
                continue
            mid = (f.left_shoulder + f.right_shoulder) / 2.0
            d = normalized_distance(acting.center, mid, shoulder_width)
            dist_score = _band_score(d, 0.0, loc.max_dist_ratio)
            below = acting.center[1] > mid[1]
            vals.append(dist_score if below else dist_score * 0.5)

    return float(np.median(vals)) if vals else 0.0


def _band_score(d: float, lo: float, hi: float) -> float:
    """1.0 inside [lo, hi]; falls off smoothly outside (over a one-band-width margin)."""
    if lo <= d <= hi:
        return 1.0
    span = max(hi - lo, hi, 1e-6)
    if d < lo:
        return float(np.clip(1.0 - (lo - d) / span, 0.0, 1.0))
    return float(np.clip(1.0 - (d - hi) / span, 0.0, 1.0))


def _vertical_score(vertical, acting_c, other_c, shoulder_width) -> float:
    """Graded vertical preference, normalized to shoulder width.

    For "above": full credit when the acting hand is level-or-above the anchor; only penalized
    when it drops CLEARLY below (a soft ramp to 0 over ~1/3 shoulder width). This avoids the old
    binary flip that snapped location to 0 every time a grinding hand dipped to the same height.
    """
    if vertical is None:
        return 1.0
    # dy > 0 when the acting hand is ABOVE the anchor (image y grows downward)
    dy = (other_c[1] - acting_c[1]) / max(shoulder_width, 1e-6)
    ramp = 0.33  # how far below (in shoulder-widths) drives the score to 0
    if vertical == "above":
        return 1.0 if dy >= 0 else float(np.clip(1.0 + dy / ramp, 0.0, 1.0))
    if vertical == "below":
        return 1.0 if dy <= 0 else float(np.clip(1.0 - dy / ramp, 0.0, 1.0))
    return 1.0


def _score_chin_reach(buffer, acting_label, shoulder_width, loc) -> float:
    """Score how close the acting hand's HIGHEST point gets to chin height, over the window.

    The hand must reach up to the chin at some point (signs like THANK YOU start there). We take
    the highest position (most-negative dy = above the shoulders) among roughly-centered frames,
    and score its closeness to the chin target. A hand that stays down at the chest never reaches
    chin height, so it scores ~0.
    """
    dys = []
    for f in buffer:
        h = f.hand(acting_label)
        if h is None or f.left_shoulder is None or f.right_shoulder is None:
            continue
        mid = (f.left_shoulder + f.right_shoulder) / 2.0
        dx = abs(h.center[0] - mid[0]) / shoulder_width
        if dx <= loc.max_dist_ratio:                       # chin is near center, not out to the side
            dys.append((h.center[1] - mid[1]) / shoulder_width)
    if not dys:
        return 0.0
    top = min(dys)                                          # highest hand position in the window
    target = -CHIN_OFFSET_RATIO                             # chin sits above the shoulder line
    return float(np.clip(1.0 - abs(top - target) / CHIN_TOL, 0.0, 1.0))


def _score_movement(buffer, sign: Sign, roles, shoulder_width) -> float:
    req = sign.movement
    if req.kind == MovementKind.NONE:
        return 1.0
    actor_label = roles.get(req.actor)
    actor_traj = _trajectory(buffer, actor_label)
    if shoulder_width is None or not actor_traj:
        return 0.0
    return mv.movement_confidence(actor_traj, shoulder_width, req)


def _score_orientation(buffer, sign: Sign, roles) -> float:
    o = sign.orientation
    label = roles.get(o.hand)
    if label is None:
        return 0.0
    vals = []
    for f in _recent(buffer, SMOOTH_SECONDS):
        h = f.hand(label)
        if h is not None:
            vals.append(ori.facing_confidence(h, o.facing))
    return float(np.median(vals)) if vals else 0.0


# ------------------------------------------------------------------ public API
def movement_debug(buffer: RollingBuffer, sign: Sign) -> str:
    """One-line readout of the live movement sub-metrics, for the dev demo / calibration."""
    req = sign.movement
    if req.kind == MovementKind.NONE:
        return "static (no movement required)"
    roles = assign_roles(buffer)
    sw = _latest_shoulder_width(buffer)
    traj = _trajectory(buffer, roles.get(req.actor))
    if req.kind == MovementKind.CIRCULAR:
        m = mv.circular_metrics(traj, sw if sw else 0.0, req)
        return (f"rot {m.net_rotation_deg:3.0f}/{req.min_total_rotation_deg:.0f}deg  "
                f"radCV {m.radius_cv:0.2f}(full<0.30)  r/sw {m.mean_r_ratio:0.2f}  "
                f"frames {m.n}  {m.duration:0.1f}s")
    return f"{req.kind.value}: {len(traj)} samples"


def location_debug(buffer: RollingBuffer, sign: Sign) -> str:
    """One-line readout of the acting hand's position vs the shoulders, for calibration.

    dy = shoulder-widths BELOW the shoulder line, dx = shoulder-widths SIDEWAYS from center.
    For a CHEST sign it also shows the target band so you can see where chest ends / belly begins.
    """
    loc = sign.location
    roles = assign_roles(buffer)
    sw = _latest_shoulder_width(buffer)
    label = roles.get(loc.acting_hand)
    for f in reversed(_recent(buffer, SMOOTH_SECONDS)):
        h = f.hand(label) if label else None
        if h is not None and f.left_shoulder is not None and sw:
            mid = (f.left_shoulder + f.right_shoulder) / 2.0
            dx = abs(h.center[0] - mid[0]) / sw
            dy = (h.center[1] - mid[1]) / sw
            if loc.anchor == Anchor.CHEST:
                lo, hi = CHEST_OFFSET_RATIO - CHEST_VBAND, CHEST_OFFSET_RATIO + CHEST_VBAND
                return f"loc dy {dy:.2f} (chest band {lo:.2f}-{hi:.2f})  dx {dx:.2f}"
            if loc.anchor == Anchor.CHIN:
                tops = [(g.hand(label).center[1] - (g.left_shoulder + g.right_shoulder)[1] / 2.0) / sw
                        for g in buffer if g.hand(label) is not None and g.left_shoulder is not None]
                top = min(tops) if tops else dy
                return f"loc top-dy {top:.2f} (chin ~ -{CHIN_OFFSET_RATIO:.2f})  now dy {dy:.2f}"
            return f"loc dy {dy:.2f}  dx {dx:.2f}  anchor={loc.anchor.value}"
    return "loc: (acting hand or shoulders not visible)"


def verify(buffer: RollingBuffer, sign: Sign) -> VerifyResult:
    roles = assign_roles(buffer)
    sw = _latest_shoulder_width(buffer)
    params: list[ParamScore] = []

    dom = sign.dominant
    params.append(ParamScore(
        "handshape_dominant",
        _score_handshape(buffer, roles.get(DOMINANT), dom.kind),
        dom.min_confidence, dom.required,
    ))

    if sign.nondominant is not None:
        nd = sign.nondominant
        params.append(ParamScore(
            "handshape_nondominant",
            _score_handshape(buffer, roles.get(NONDOMINANT), nd.kind),
            nd.min_confidence, nd.required,
        ))

    params.append(ParamScore(
        "location",
        _score_location(buffer, sign, roles, sw),
        sign.location.min_confidence, sign.location.required,
    ))

    params.append(ParamScore(
        "movement",
        _score_movement(buffer, sign, roles, sw),
        sign.movement.min_confidence, sign.movement.required,
    ))

    if sign.orientation is not None:
        params.append(ParamScore(
            "orientation",
            _score_orientation(buffer, sign, roles),
            sign.orientation.min_confidence, sign.orientation.required,
        ))

    return VerifyResult(sign.name, params, roles)
