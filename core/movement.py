"""Movement detectors over the rolling buffer — the core of the anti-bug fix.

Each detector reads a *trajectory* (a list of (t, center) samples spanning the window), never a
single frame. Confidences are in [0, 1].

  - circular: the acting hand's center is measured by its angle about the CENTROID of its own
    path (the local circle center). We unwrap that angle across frames and sum the rotation;
    we also check the radius about the centroid stays steady. A real grind clears both; a hand
    that wandered randomly fails the radius check; a motionless hand has ~zero radius and scores
    0. (The non-dominant fist is handled by the LOCATION check, not here — movement only asks
    "did this hand trace a circle".)
  - linear: window start->end displacement, checked for magnitude, direction, and monotonic
    progression (not jitter).
  - repeated: number of oscillation cycles in the distance-from-mean signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.schema import MovementKind, MovementReq

# Radius coefficient-of-variation below which a circle gets FULL radius credit. Real human
# grinding is never a perfect circle, so we don't start penalizing until cv exceeds this.
_RADIUS_CV_FREE = 0.30


def _series(traj):
    ts = np.array([t for t, _ in traj], dtype=float)
    pts = np.array([np.asarray(c, dtype=float) for _, c in traj], dtype=float)
    return ts, pts


@dataclass
class CircularMetrics:
    """Sub-scores behind a circular-movement confidence — surfaced for live calibration."""

    score: float
    net_rotation_deg: float
    radius_cv: float
    mean_r_ratio: float       # mean radius as a fraction of shoulder width
    n: int
    duration: float


def circular_metrics(actor_traj, shoulder_width: float, req: MovementReq) -> CircularMetrics:
    """Measure how circular the acting hand's path is about its own centroid.

    Two ingredients, combined multiplicatively:
      - rotation: total unwrapped angle swept about the path centroid vs. req threshold.
      - radius steadiness: a real circle keeps a roughly constant radius; we give full credit
        until the radius coefficient-of-variation exceeds _RADIUS_CV_FREE, then fall off over
        req.radius_tolerance_ratio. This rejects "hand wandered randomly" without demanding a
        machine-perfect circle from a human grind.
    """
    n = len(actor_traj)
    if n < 5 or shoulder_width is None or shoulder_width <= 0:
        return CircularMetrics(0.0, 0.0, 99.0, 0.0, n, 0.0)

    ts, a = _series(actor_traj)
    duration = float(ts[-1] - ts[0])
    pivot = a.mean(axis=0)                 # local circle center
    rel = a - pivot
    radii = np.linalg.norm(rel, axis=1)
    mean_r = float(radii.mean())
    mean_r_ratio = mean_r / shoulder_width
    angles = np.unwrap(np.arctan2(rel[:, 1], rel[:, 0]))
    net_rotation = abs(float(np.degrees(angles[-1] - angles[0])))
    radius_cv = float(radii.std() / mean_r) if mean_r > 1e-6 else 99.0

    # Gate: enough time, and an actual orbit (a near-still hand orbits nothing).
    if duration < req.min_duration_s or mean_r_ratio < 0.03:
        return CircularMetrics(0.0, net_rotation, radius_cv, mean_r_ratio, n, duration)

    rotation_score = float(np.clip(net_rotation / req.min_total_rotation_deg, 0.0, 1.0))
    radius_excess = max(0.0, radius_cv - _RADIUS_CV_FREE)
    radius_score = float(np.clip(1.0 - radius_excess / max(req.radius_tolerance_ratio, 1e-6), 0.0, 1.0))
    score = rotation_score * radius_score
    return CircularMetrics(score, net_rotation, radius_cv, mean_r_ratio, n, duration)


def circular_confidence(actor_traj, shoulder_width: float, req: MovementReq) -> float:
    return circular_metrics(actor_traj, shoulder_width, req).score


def linear_confidence(actor_traj, shoulder_width: float, req: MovementReq) -> float:
    if len(actor_traj) < 3 or shoulder_width is None or shoulder_width <= 0:
        return 0.0
    ts, a = _series(actor_traj)
    if ts[-1] - ts[0] < req.min_duration_s:
        return 0.0

    disp = a[-1] - a[0]
    mag = float(np.linalg.norm(disp))
    if mag < 1e-6:
        return 0.0
    mag_score = float(np.clip((mag / shoulder_width) / req.min_displacement_ratio, 0.0, 1.0))

    unit = disp / mag
    dir_score = 1.0
    if req.direction is not None:
        d = np.asarray(req.direction, dtype=float)
        dn = np.linalg.norm(d)
        if dn > 1e-6:
            dir_score = float(np.clip(unit @ (d / dn), 0.0, 1.0))

    proj = a @ unit
    steps = np.diff(proj)
    monotonic = float(np.mean(steps > 0)) if len(steps) else 0.0
    return mag_score * dir_score * monotonic


def repeated_confidence(actor_traj, shoulder_width: float, req: MovementReq) -> float:
    if len(actor_traj) < 6:
        return 0.0
    ts, a = _series(actor_traj)
    if ts[-1] - ts[0] < req.min_duration_s:
        return 0.0

    signal = np.linalg.norm(a - a.mean(axis=0), axis=1)
    signal = signal - signal.mean()
    if np.allclose(signal, 0):
        return 0.0
    signs = np.sign(signal)
    signs[signs == 0] = 1
    crossings = int(np.sum(np.abs(np.diff(signs)) > 0))
    cycles = crossings / 2.0
    return float(np.clip(cycles / max(req.min_cycles, 1), 0.0, 1.0))


def movement_confidence(actor_traj, shoulder_width: float, req: MovementReq) -> float:
    """Dispatch on the required movement kind. NONE is trivially satisfied (no motion needed)."""
    if req.kind == MovementKind.NONE:
        return 1.0
    if req.kind == MovementKind.CIRCULAR:
        return circular_confidence(actor_traj, shoulder_width, req)
    if req.kind == MovementKind.LINEAR:
        return linear_confidence(actor_traj, shoulder_width, req)
    if req.kind == MovementKind.REPEATED:
        return repeated_confidence(actor_traj, shoulder_width, req)
    return 0.0
