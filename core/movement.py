"""Movement detectors over the rolling buffer — the core of the anti-bug fix.

Every detector takes trajectories already extracted from the buffer (the verifier does the
role -> hand resolution) plus a `shoulder_width` for scale, and returns a confidence in [0, 1].
A static hold yields ~0 from every motion detector, which is exactly why a frozen pose can never
satisfy a movement-required sign.

  - linear(ts, pts, direction, min_displacement_ratio): net travel along a direction + monotonic
    progress. Used by HELP (both hands rising).
  - converge(pts_a, pts_b, min_approach_ratio): the gap between two hands shrinking. Used by PAIN.
  - repeated(ts, pts, min_cycles, min_speed_ratio): oscillation cycles along the principal axis of
    motion, with an optional speed gate for "rapid". Used by MEDICINE (twist) and EMERGENCY (shake).
  - circular(ts, pts, pivot, ...): summed unwrapped rotation about a pivot with a radius-stability
    check. Not used by hospital v1, kept for the shared engine (coffee-shop COFFEE).

All distances are divided by `shoulder_width`, so thresholds are scale-invariant.
"""
from __future__ import annotations

import numpy as np


def _as_xy(pts) -> np.ndarray:
    a = np.asarray(pts, dtype=float)
    return a.reshape(-1, 2)


def linear(ts, pts, direction, min_displacement_ratio: float, shoulder_width: float) -> float:
    """Net displacement along `direction` (in shoulder widths) + monotonic progression.

    direction is an image-space vector (up = (0, -1)). Returns 0 for a static hold (no travel)
    and approaches 1 when the hand travels at least `min_displacement_ratio` along `direction`
    without backtracking.
    """
    pts = _as_xy(pts)
    if len(pts) < 2 or shoulder_width <= 0:
        return 0.0

    d = np.asarray(direction, dtype=float)
    d = d / (np.linalg.norm(d) + 1e-9)

    # Projection of each point (relative to start) onto the desired direction, in shoulder widths.
    rel = (pts - pts[0]) @ d / shoulder_width
    net = float(rel[-1])                                   # signed travel along direction

    if min_displacement_ratio > 0:
        mag = np.clip(net / min_displacement_ratio, 0.0, 1.0)
    else:
        mag = 1.0 if net > 0 else 0.0

    # Monotonic progress: fraction of steps that move forward along the direction.
    steps = np.diff(rel)
    mono = float(np.mean(steps > 0)) if len(steps) else 0.0

    return float(np.clip(mag * (0.5 + 0.5 * mono), 0.0, 1.0))


def converge(pts_a, pts_b, min_approach_ratio: float, shoulder_width: float) -> float:
    """How much the gap between two hands shrinks over the window (in shoulder widths).

    `pts_a`/`pts_b` are aligned frame-by-frame (same length). Returns ~0 if the hands hold a
    constant distance, approaching 1 as the gap closes by at least `min_approach_ratio`.
    """
    pts_a, pts_b = _as_xy(pts_a), _as_xy(pts_b)
    n = min(len(pts_a), len(pts_b))
    if n < 2 or shoulder_width <= 0:
        return 0.0

    gap = np.linalg.norm(pts_a[:n] - pts_b[:n], axis=1) / shoulder_width
    k = max(1, n // 4)
    start = float(np.mean(gap[:k]))
    end = float(np.mean(gap[-k:]))
    approach = start - end                                  # positive when hands come together

    if min_approach_ratio > 0:
        mag = np.clip(approach / min_approach_ratio, 0.0, 1.0)
    else:
        mag = 1.0 if approach > 0 else 0.0

    # Reward a steady close rather than a jittery one.
    steps = np.diff(gap)
    mono = float(np.mean(steps < 0)) if len(steps) else 0.0

    return float(np.clip(mag * (0.5 + 0.5 * mono), 0.0, 1.0))


def _principal_projection(pts: np.ndarray) -> np.ndarray:
    """Project a 2D path onto its axis of greatest variance (the main line of motion)."""
    centered = pts - pts.mean(axis=0)
    # Principal axis via the covariance eigenvector of the largest eigenvalue.
    cov = centered.T @ centered
    eigvals, eigvecs = np.linalg.eigh(cov)
    axis = eigvecs[:, int(np.argmax(eigvals))]
    return centered @ axis


def repeated(ts, pts, min_cycles: int, min_speed_ratio: float, shoulder_width: float) -> float:
    """Oscillation cycles along the principal axis of motion, with an optional speed gate.

    Counts how many times the motion reverses (back-and-forth) above a small noise floor, then
    converts to cycles. For "rapid" signs (EMERGENCY) a `min_speed_ratio` gate also requires the
    hand to actually move fast. A static hold has no reversals and no speed -> 0.
    """
    pts = _as_xy(pts)
    ts = np.asarray(ts, dtype=float)
    if len(pts) < 4 or shoulder_width <= 0:
        return 0.0

    proj = _principal_projection(pts)
    noise_floor = 0.04 * shoulder_width                    # ignore sub-jitter wiggles

    # Count sign changes of the centered signal that exceed the noise floor -> half-oscillations.
    crossings = 0
    last_sign = 0
    for v in proj:
        if abs(v) < noise_floor:
            continue
        s = 1 if v > 0 else -1
        if last_sign != 0 and s != last_sign:
            crossings += 1
        last_sign = s
    cycles = crossings / 2.0
    cycle_score = np.clip(cycles / max(1, min_cycles), 0.0, 1.0)

    # Speed gate (mean path length per second, in shoulder widths/sec).
    duration = float(ts[-1] - ts[0]) if len(ts) >= 2 else 0.0
    if min_speed_ratio > 0:
        if duration <= 0:
            return 0.0
        path = float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))) / shoulder_width
        mean_speed = path / duration
        speed_score = np.clip(mean_speed / min_speed_ratio, 0.0, 1.0)
    else:
        speed_score = 1.0

    return float(np.clip(cycle_score * speed_score, 0.0, 1.0))


def circular(ts, pts, pivot, min_total_rotation_deg: float, radius_tolerance_ratio: float) -> float:
    """Summed unwrapped rotation about a pivot, gated by radius stability.

    Not used by hospital v1; retained so the shared engine can verify the coffee-shop COFFEE sign
    (dominant hand circling over the non-dominant fist) without a second code path.
    """
    pts = _as_xy(pts)
    pivot = _as_xy(pivot)
    n = min(len(pts), len(pivot))
    if n < 4:
        return 0.0

    rel = pts[:n] - pivot[:n]
    angles = np.unwrap(np.arctan2(rel[:, 1], rel[:, 0]))
    total_deg = abs(float(np.degrees(angles[-1] - angles[0])))
    rot_score = np.clip(total_deg / max(1.0, min_total_rotation_deg), 0.0, 1.0)

    radii = np.linalg.norm(rel, axis=1)
    mean_r = float(np.mean(radii)) + 1e-9
    radius_var = float(np.std(radii)) / mean_r              # coefficient of variation
    radius_ok = np.clip(1.0 - radius_var / max(1e-6, radius_tolerance_ratio), 0.0, 1.0)

    return float(np.clip(rot_score * radius_ok, 0.0, 1.0))
