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
            vert_score = _vertical_score(loc.vertical, acting.center, other.center)
            vals.append(min(dist_score, vert_score))
        else:  # NEUTRAL_SPACE — in front of the torso, below the shoulders
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


def _vertical_score(vertical, acting_c, other_c) -> float:
    if vertical is None:
        return 1.0
    # image y points down: "above" means smaller y
    if vertical == "above":
        return 1.0 if acting_c[1] < other_c[1] else 0.0
    if vertical == "below":
        return 1.0 if acting_c[1] > other_c[1] else 0.0
    return 1.0


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
