"""Movement detectors over the rolling buffer — the core of the anti-bug fix.

Each detector reads a *trajectory* (a list of (t, center) samples spanning the window), never a
single frame. Confidences are in [0, 1].

  - circular: the acting hand's center angle about its own path centroid; unwrapped + summed;
    radius stability check rejects random wandering. Calibrated on real hands (_RADIUS_CV_FREE).
  - linear: window start->end displacement, direction, and monotonic progression.
  - repeated: oscillation cycles in the distance-from-mean signal.
  - converge: two-hand version — gap between both hands closing over the window (PAIN).
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
    mean_r_ratio: float
    n: int
    duration: float


def circular_metrics(actor_traj, shoulder_width: float, req: MovementReq) -> CircularMetrics:
    """Measure how circular the acting hand's path is about its own centroid."""
    n = len(actor_traj)
    if n < 5 or shoulder_width is None or shoulder_width <= 0:
        return CircularMetrics(0.0, 0.0, 99.0, 0.0, n, 0.0)

    ts, a = _series(actor_traj)
    duration = float(ts[-1] - ts[0])
    pivot = a.mean(axis=0)
    rel = a - pivot
    radii = np.linalg.norm(rel, axis=1)
    mean_r = float(radii.mean())
    mean_r_ratio = mean_r / shoulder_width
    angles = np.unwrap(np.arctan2(rel[:, 1], rel[:, 0]))
    net_rotation = abs(float(np.degrees(angles[-1] - angles[0])))
    radius_cv = float(radii.std() / mean_r) if mean_r > 1e-6 else 99.0

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
    mag_ratio = mag / shoulder_width
    # Hard floor: a near-still hand (incidental jitter/repositioning) is never "linear motion",
    # regardless of the sign's min_displacement_ratio.
    if mag_ratio < 0.05:
        return 0.0
    mag_score = float(np.clip(mag_ratio / req.min_displacement_ratio, 0.0, 1.0))

    unit = disp / mag
    dir_score = 1.0
    if req.direction is not None:
        d = np.asarray(req.direction, dtype=float)
        dn = np.linalg.norm(d)
        if dn > 1e-6:
            dir_score = float(np.clip(unit @ (d / dn), 0.0, 1.0))

    # Monotonic progression is intentionally NOT required: net displacement (mag) + direction
    # already reject jitter and back-and-forth (which have small net displacement), and demanding
    # strict frame-by-frame monotonicity made real human motion feel stiff / fail intermittently.
    return mag_score * dir_score


def repeated_confidence(actor_traj, shoulder_width: float, req: MovementReq) -> float:
    if len(actor_traj) < 6 or shoulder_width is None or shoulder_width <= 0:
        return 0.0
    ts, a = _series(actor_traj)
    if ts[-1] - ts[0] < req.min_duration_s:
        return 0.0

    # distance of the hand from the centroid of its own path
    signal = np.linalg.norm(a - a.mean(axis=0), axis=1)

    # A genuine repeated motion has real AMPLITUDE. Reject jitter / a near-still hand outright —
    # this is what stops a barely-moving claw from racking up false "cycles" and passing.
    amp_ratio = float(signal.max() - signal.min()) / shoulder_width
    if amp_ratio < 0.05:
        return 0.0

    centered = signal - signal.mean()
    # Count direction reversals only when the swing clears a noise band, so micro-wiggles near the
    # mean don't inflate the cycle count.
    noise = 0.25 * float(np.max(np.abs(centered)))
    crossings, last = 0, 0
    for v in centered:
        if abs(v) < noise:
            continue
        cur = 1 if v > 0 else -1
        if last != 0 and cur != last:
            crossings += 1
        last = cur
    cycles = crossings / 2.0

    cycle_score = float(np.clip(cycles / max(req.min_cycles, 1), 0.0, 1.0))
    amp_score = float(np.clip(amp_ratio / 0.08, 0.0, 1.0))
    # Need BOTH enough cycles AND enough amplitude: a tiny tremor with many reversals fails on
    # amplitude; a single big sweep with no reversals fails on cycles.
    return float(min(cycle_score, amp_score))


def converge_confidence(traj_a, traj_b, shoulder_width: float, req: MovementReq) -> float:
    """How much the gap between two hands shrinks over the window.

    `traj_a` and `traj_b` are aligned frame-by-frame trajectories for the two hands (only frames
    where both are present). Returns ~0 for a static held-apart pose, approaching 1 as the hands
    close by at least `req.min_approach_ratio` shoulder widths with a roughly steady approach.
    """
    n = min(len(traj_a), len(traj_b))
    if n < 3 or shoulder_width <= 0:
        return 0.0

    ts = np.array([t for t, _ in traj_a[:n]], dtype=float)
    if ts[-1] - ts[0] < req.min_duration_s:
        return 0.0

    pts_a = np.array([np.asarray(c, float) for _, c in traj_a[:n]])
    pts_b = np.array([np.asarray(c, float) for _, c in traj_b[:n]])
    gap = np.linalg.norm(pts_a - pts_b, axis=1) / shoulder_width

    k = max(1, n // 4)
    approach = float(np.mean(gap[:k])) - float(np.mean(gap[-k:]))   # positive = hands closing

    mono = float(np.mean(np.diff(gap) < 0)) if n > 1 else 0.0

    if req.min_approach_ratio > 0:
        mag = float(np.clip(approach / req.min_approach_ratio, 0.0, 1.0))
    else:
        mag = 1.0 if approach > 0 else 0.0

    return float(np.clip(mag * (0.5 + 0.5 * mono), 0.0, 1.0))


def movement_confidence(actor_traj, shoulder_width: float, req: MovementReq) -> float:
    """Dispatch on the required movement kind. NONE trivially satisfied; CONVERGE uses two trajs."""
    if req.kind == MovementKind.NONE:
        return 1.0
    if req.kind == MovementKind.CIRCULAR:
        return circular_confidence(actor_traj, shoulder_width, req)
    if req.kind == MovementKind.LINEAR:
        return linear_confidence(actor_traj, shoulder_width, req)
    if req.kind == MovementKind.REPEATED:
        return repeated_confidence(actor_traj, shoulder_width, req)
    # CONVERGE needs two trajectories — called directly from the verifier; return 0 if reached here.
    return 0.0
