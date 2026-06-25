"""Generic temporal verifier — one engine for every sign.

`verify(buffer, sign)` reads the rolling landmark buffer plus a Sign definition and returns a
per-parameter confidence breakdown {handshape, location, movement, orientation} in [0, 1], the
threshold each parameter had to clear, and an overall `passed`.

The pass rule is the whole point: `passed` is True **iff every parameter the sign marks required
individually clears its threshold**. There is no averaging anywhere — a perfect handshape can
never compensate for absent required movement. That is what makes the original single-frame
COFFEE bug structurally impossible: HELP/PAIN/MEDICINE/EMERGENCY all mark movement required, and a
frozen pose scores ~0 on movement, so they fail on movement specifically.

Role resolution: signs talk about "dominant"/"nondominant" roles, not Left/Right hands. We don't
trust mirror-flipped handedness labels, so for each candidate role->hand assignment we score the
whole sign and keep the best-scoring assignment. One-handed signs try each detected hand as the
dominant; two-handed signs try both orderings of the two detected hands.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from core import handshape, movement, orientation
from core.landmarks import RollingBuffer, Frame
from core.schema import Sign


@dataclass
class VerifyResult:
    """The full, explainable outcome of one verification."""

    passed: bool
    scores: dict[str, float]                  # handshape, location, movement, orientation in [0,1]
    thresholds: dict[str, float]              # the cutoff each parameter had to clear
    required: tuple[str, ...]                 # which parameters were gated for this sign
    failed: tuple[str, ...] = ()              # required parameters that did NOT clear
    note: str = ""

    def __str__(self) -> str:
        bits = "  ".join(f"{k}={self.scores[k]:.2f}" for k in ("handshape", "location", "movement", "orientation"))
        verdict = "PASS" if self.passed else f"FAIL({','.join(self.failed) or '-'})"
        return f"[{verdict}] {bits}"


# ---------------------------------------------------------------------------
# Trajectory / scale extraction from the buffer
# ---------------------------------------------------------------------------

def _frames(buffer) -> list[Frame]:
    return list(buffer) if not isinstance(buffer, list) else buffer


def _labels(frames: list[Frame]) -> list[str]:
    """Distinct handedness labels seen, preferring the most recent complete frame's order."""
    for f in reversed(frames):
        if len(f.hands) >= 2:
            return [f.hands[0].handedness, f.hands[1].handedness]
    for f in reversed(frames):
        if f.hands:
            return [f.hands[0].handedness]
    return []


def _shoulder_width(frames: list[Frame]) -> float:
    widths = [f.shoulder_width for f in frames if f.shoulder_width]
    if widths:
        return float(np.median(widths))
    # Fallback so the demo still runs if pose flickers: a fraction of image width.
    img_w = float(np.median([f.width for f in frames])) if frames else 640.0
    return 0.25 * img_w


def _hand_traj(frames: list[Frame], label: str):
    """(ts, pts) for the palm center of the hand matching `label`, over frames where it's present."""
    ts, pts = [], []
    for f in frames:
        h = f.hand(label)
        if h is not None:
            ts.append(f.t)
            pts.append(h.center)
    return np.asarray(ts, float), np.asarray(pts, float).reshape(-1, 2)


def _both_traj(frames: list[Frame], a: str, b: str):
    """(ts, mean-of-two-palm-centers) over frames where BOTH hands are present."""
    ts, pts = [], []
    for f in frames:
        ha, hb = f.hand(a), f.hand(b)
        if ha is not None and hb is not None:
            ts.append(f.t)
            pts.append((ha.center + hb.center) / 2.0)
    return np.asarray(ts, float), np.asarray(pts, float).reshape(-1, 2)


def _aligned_pair(frames: list[Frame], a: str, b: str):
    """Frame-aligned palm-center paths for two hands (only frames where both are present)."""
    pa, pb = [], []
    for f in frames:
        ha, hb = f.hand(a), f.hand(b)
        if ha is not None and hb is not None:
            pa.append(ha.center)
            pb.append(hb.center)
    return np.asarray(pa, float).reshape(-1, 2), np.asarray(pb, float).reshape(-1, 2)


def _mean_handshape(frames: list[Frame], label: str, kind: str) -> float:
    """Average per-frame handshape confidence over frames where the hand is present (smoothing)."""
    vals = [handshape.score(h, kind) for f in frames if (h := f.hand(label)) is not None]
    return float(np.mean(vals)) if vals else 0.0


# ---------------------------------------------------------------------------
# Per-parameter scoring for one fixed role->label assignment
# ---------------------------------------------------------------------------

def _location_score(frames, sign: Sign, dom_label: str, nondom_label: Optional[str], sw: float) -> float:
    loc = sign.location
    if loc.anchor == "neutral":
        return 1.0                                       # neutral space is unconstrained in v1
    if loc.anchor == "nondominant_palm":
        if nondom_label is None:
            return 0.0
        dists = []
        for f in frames:
            hd, hn = f.hand(dom_label), f.hand(nondom_label)
            if hd is not None and hn is not None:
                dists.append(float(np.linalg.norm(hd.center - hn.center)) / sw)
        if not dists:
            return 0.0
        dist = float(np.median(dists))
        margin = loc.max_dist_ratio
        return float(np.clip(1.0 - max(0.0, dist - margin) / margin, 0.0, 1.0))
    return 1.0                                            # unknown anchor: don't block in v1


def _movement_score(frames, sign: Sign, dom_label: str, nondom_label: Optional[str], sw: float) -> float:
    mv = sign.movement
    if mv.kind == "none":
        return 1.0

    if mv.kind == "linear":
        if mv.actor == "both" and nondom_label is not None:
            ts, pts = _both_traj(frames, dom_label, nondom_label)
        else:
            ts, pts = _hand_traj(frames, dom_label)
        return movement.linear(ts, pts, mv.direction, mv.min_displacement_ratio, sw)

    if mv.kind == "converge":
        if nondom_label is None:
            return 0.0
        pa, pb = _aligned_pair(frames, dom_label, nondom_label)
        return movement.converge(pa, pb, mv.min_approach_ratio, sw)

    if mv.kind == "repeated":
        ts, pts = _hand_traj(frames, dom_label)
        return movement.repeated(ts, pts, mv.min_cycles, mv.min_speed_ratio, sw)

    if mv.kind == "circular":
        ts, pts = _hand_traj(frames, dom_label)
        if mv.reference == "nondominant_center" and nondom_label is not None:
            _, pivot = _hand_traj(frames, nondom_label)
        else:
            pivot = np.tile(pts.mean(axis=0), (len(pts), 1)) if len(pts) else pts
        return movement.circular(ts, pts, pivot, mv.min_total_rotation_deg, mv.radius_tolerance_ratio)

    return 0.0


def _orientation_score(frames, sign: Sign, dom_label: str, nondom_label: Optional[str]) -> float:
    po = sign.palm_orientation
    if po is None:
        return 1.0
    label = dom_label if po.hand == "dominant" else nondom_label
    if label is None:
        return 0.5
    vals = [orientation.score(h, po.facing) for f in frames if (h := f.hand(label)) is not None]
    return float(np.mean(vals)) if vals else 0.5


def _score_assignment(frames, sign: Sign, dom_label: str, nondom_label: Optional[str], sw: float) -> dict:
    """All four parameter scores for one fixed role->label assignment."""
    dom_score = _mean_handshape(frames, dom_label, sign.dominant.kind)
    if sign.nondominant is not None:
        nd_score = _mean_handshape(frames, nondom_label, sign.nondominant.kind) if nondom_label else 0.0
        hs = min(dom_score, nd_score)                    # both hands must match: weakest hand wins
    else:
        hs = dom_score
    return {
        "handshape": hs,
        "location": _location_score(frames, sign, dom_label, nondom_label, sw),
        "movement": _movement_score(frames, sign, dom_label, nondom_label, sw),
        "orientation": _orientation_score(frames, sign, dom_label, nondom_label),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify(buffer, sign: Sign) -> VerifyResult:
    """Score `sign` against the rolling `buffer` and apply required-gating (no averaging)."""
    frames = _frames(buffer)
    sw = _shoulder_width(frames)
    labels = _labels(frames)

    # Candidate role->label assignments (we keep the best-scoring one).
    candidates: list[tuple[str, Optional[str]]] = []
    if sign.two_handed:
        if len(labels) >= 2:
            candidates = [(labels[0], labels[1]), (labels[1], labels[0])]
        elif len(labels) == 1:
            candidates = [(labels[0], None)]
    else:
        candidates = [(lab, None) for lab in labels] or []

    # Per-parameter thresholds for this sign.
    thresholds = {
        "handshape": sign.dominant.threshold,
        "location": sign.location.threshold,
        "movement": sign.movement.threshold,
        "orientation": sign.palm_orientation.threshold if sign.palm_orientation else 0.0,
    }
    required = sign.required_parameters()

    if not candidates:
        zero = {k: 0.0 for k in ("handshape", "location", "movement", "orientation")}
        return VerifyResult(False, zero, thresholds, required, failed=required, note="no hands detected")

    # Score every candidate; rank by required-params passing, then by their summed confidence.
    best = None
    best_key = None
    for dom_label, nondom_label in candidates:
        scores = _score_assignment(frames, sign, dom_label, nondom_label, sw)
        failed = tuple(p for p in required if scores[p] < thresholds[p])
        passed = len(failed) == 0
        key = (passed, sum(scores[p] for p in required) if required else sum(scores.values()))
        if best_key is None or key > best_key:
            best_key, best = key, (scores, failed, passed)

    scores, failed, passed = best
    return VerifyResult(passed, scores, thresholds, required, failed=failed)
