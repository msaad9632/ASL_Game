"""Generate deterministic synthetic landmark fixtures for the confusor regression tests.

These are NOT webcam recordings — they are geometrically constructed landmark clips, so the test
suite is reproducible in CI (no camera) and exercises the verifier's gating precisely:

  - <name>_correct.json  performs the real motion and clears every required parameter.
  - <name>_confusor.json freezes the SAME handshape with NO motion, so it fails on the MOVEMENT
    parameter specifically (the anti-bug guarantee).

Hands are built by placing the 21 landmarks the classifiers actually read (wrist, finger MCPs and
tips, thumb tip) to hit a target handshape, then translating/oscillating the whole hand over time
to create the motion. Distances are in pixels against a fixed synthetic shoulder width.

To replace any fixture with a REAL recording (preferred for dataset-building), just record over
the same filename with the now-fixed recorder:
    python -m tools.record_fixture --name help_correct --seconds 4 --sign HELP

Regenerate all synthetic fixtures:
    python -m tools.make_synth_fixtures
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from core.landmarks import (
    Frame, Hand,
    WRIST, THUMB_TIP,
    INDEX_MCP, INDEX_TIP, MIDDLE_MCP, MIDDLE_TIP,
    RING_MCP, RING_TIP, PINKY_MCP, PINKY_TIP,
)

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# --- synthetic frame geometry (pixels) ---
W, H = 640, 480
CX = 320.0
SY = 120.0
SW = 240.0                      # shoulder width in px
LS = np.array([CX - SW / 2, SY])
RS = np.array([CX + SW / 2, SY])
N = 60                          # frames per clip
T = 2.0                         # seconds per clip
D = 70.0                        # within-hand scale (wrist -> MCP) in px

UP = np.array([0.0, -1.0])
_MCPS = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
_X_OFF = [-0.27, -0.09, 0.09, 0.27]            # index..pinky horizontal MCP offsets (x D)

# tip/MCP distance ratio per finger that core.handshape._finger_curl maps to a curl:
#   ratio 1.6 -> curl 0 (extended);  ratio 1.0 -> curl 1 (curled);  ratio 1.3 -> curl ~0.5 (claw)
_RATIOS = {
    "open":  [1.6, 1.6, 1.6, 1.6],
    "fist":  [1.0, 1.0, 1.0, 1.0],
    "a":     [1.0, 1.0, 1.0, 1.0],
    "index": [1.6, 1.0, 1.0, 1.0],
    "claw":  [1.3, 1.3, 1.3, 1.3],
}

# fill (unused-by-scorers) joints so each hand is a plausible 21-point array
_SEG = {(INDEX_MCP, INDEX_TIP): (6, 7), (MIDDLE_MCP, MIDDLE_TIP): (10, 11),
        (RING_MCP, RING_TIP): (14, 15), (PINKY_MCP, PINKY_TIP): (18, 19)}


def make_hand(handedness: str, center_target, shape: str) -> Hand:
    """Build a 21-landmark hand whose palm-center sits at `center_target`, forming `shape`."""
    center_target = np.asarray(center_target, float)
    # hand.center = c + (0, -0.3D) for this layout, so offset c to land center on target.
    c = center_target + np.array([0.0, 0.3 * D])
    pts = np.zeros((21, 3))
    wrist = c + np.array([0.0, 0.5 * D])
    pts[WRIST, :2] = wrist

    ratios = _RATIOS[shape]
    for k in range(4):
        mcp = wrist + UP * D + np.array([_X_OFF[k] * D, 0.0])
        v = mcp - wrist
        u = v / (np.linalg.norm(v) + 1e-9)
        tip = wrist + u * (ratios[k] * np.linalg.norm(v))
        pts[_MCPS[k], :2] = mcp
        pts[_TIPS[k], :2] = tip

    # thumb: extended alongside for "a", tucked near the index MCP otherwise
    if shape == "a":
        pts[THUMB_TIP, :2] = wrist + UP * (0.2 * D) + np.array([-1.05 * D, 0.0])
    else:
        pts[THUMB_TIP, :2] = pts[INDEX_MCP, :2] + np.array([-0.15 * D, 0.10 * D])

    # plausible filler joints (thumb 1-3 and finger PIP/DIP) — not read by the classifiers
    for j, frac in ((1, 0.25), (2, 0.5), (3, 0.75)):
        pts[j, :2] = wrist * (1 - frac) + pts[THUMB_TIP, :2] * frac
    for (mcp, tip), (a, b) in _SEG.items():
        pts[a, :2] = pts[mcp, :2] * 0.66 + pts[tip, :2] * 0.34
        pts[b, :2] = pts[mcp, :2] * 0.33 + pts[tip, :2] * 0.67
    return Hand(handedness=handedness, points=pts)


def _frame(t: float, hands: list[Hand]) -> Frame:
    return Frame(t=t, width=W, height=H, hands=hands,
                 left_shoulder=LS.copy(), right_shoulder=RS.copy())


def _write(name: str, sign_name: str, frames: list[Frame]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"sign_name": sign_name, "synthetic": True,
            "frames": [f.to_dict() for f in frames]}
    with open(OUT / f"{name}.json", "w") as fh:
        json.dump(data, fh)
    print(f"wrote {name}.json  ({len(frames)} frames, {frames[-1].t - frames[0].t:.1f}s)")


# --------------------------------------------------------------- per-sign clip builders
def _ts():
    return [i * (T / (N - 1)) for i in range(N)]


# Each clip is built in one of three modes:
#   "correct"  — performs the sign's real motion (must PASS)
#   "confusor" — freezes the correct handshape with NO motion (must FAIL on movement)
#   "idle"     — correct-ish handshapes held with small incidental JITTER, no sign motion: the
#                "user is present but not performing the sign" case (must FAIL on movement)
_JIT = np.random.default_rng(20260627)            # fixed seed -> reproducible idle fixtures


def _jit(scale: float = 2.0) -> np.ndarray:
    return _JIT.normal(0.0, scale, size=2)


def _progress(i: int, mode: str) -> float:
    return (i / (N - 1)) if mode == "correct" else 0.0   # confusor & idle make no sign progress


def help_clip(mode: str) -> list[Frame]:
    dom0, ndom0 = np.array([CX, 228.0]), np.array([CX, 300.0])   # fist stacked above open palm
    out = []
    for i, t in enumerate(_ts()):
        fr = _progress(i, mode)
        dom = dom0 + np.array([0.0, -70.0 * fr])                 # dominant (fist) rises a bit more...
        ndom = ndom0 + np.array([0.0, -55.0 * fr])               # ...so it's the higher-motion hand
        if mode == "idle":
            dom, ndom = dom + _jit(), ndom + _jit()
        out.append(_frame(t, [make_hand("Right", dom, "fist"), make_hand("Left", ndom, "open")]))
    return out


def pain_clip(mode: str) -> list[Frame]:
    dom0, ndom0 = np.array([CX - 100.0, 280.0]), np.array([CX + 100.0, 280.0])
    dom1, ndom1 = np.array([CX - 30.0, 280.0]), np.array([CX + 30.0, 280.0])
    out = []
    for i, t in enumerate(_ts()):
        fr = _progress(i, mode)
        dom = dom0 + (dom1 - dom0) * fr
        ndom = ndom0 + (ndom1 - ndom0) * fr
        if mode == "idle":
            dom, ndom = dom + _jit(), ndom + _jit()
        out.append(_frame(t, [make_hand("Right", dom, "index"), make_hand("Left", ndom, "index")]))
    return out


def medicine_clip(mode: str) -> list[Frame]:
    ndom = np.array([CX, 300.0])                                 # open palm held still
    out = []
    for t in _ts():
        dx = 25.0 * math.sin(2 * math.pi * 1.5 * t) if mode == "correct" else 0.0
        dom = np.array([CX + dx, 228.0])                         # claw rocks over the palm
        nd = ndom.copy()
        if mode == "idle":
            dom, nd = dom + _jit(), nd + _jit()
        out.append(_frame(t, [make_hand("Right", dom, "claw"), make_hand("Left", nd, "open")]))
    return out


def emergency_clip(mode: str) -> list[Frame]:
    out = []
    for t in _ts():
        dx = 30.0 * math.sin(2 * math.pi * 2.0 * t) if mode == "correct" else 0.0
        dom = np.array([CX + dx, 220.0])                         # single claw shaken fast
        if mode == "idle":
            dom = dom + _jit()
        out.append(_frame(t, [make_hand("Right", dom, "claw")]))
    return out


BUILDERS = {
    "help": ("HELP", help_clip),
    "pain": ("PAIN", pain_clip),
    "medicine": ("MEDICINE", medicine_clip),
    "emergency": ("EMERGENCY", emergency_clip),
}


def main() -> None:
    for base, (sign_name, builder) in BUILDERS.items():
        _write(f"{base}_correct", sign_name, builder("correct"))
        _write(f"{base}_confusor", sign_name, builder("confusor"))
        _write(f"{base}_idle", sign_name, builder("idle"))


if __name__ == "__main__":
    main()
