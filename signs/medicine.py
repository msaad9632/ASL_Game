"""MEDICINE — repeated twisting movement over the non-dominant palm.

ASL MEDICINE: the non-dominant hand is an open, upward palm; the dominant hand (middle finger
toward the palm — approximated as a "claw" in v1) touches the palm center and **rocks/twists back
and forth repeatedly**. The defining feature is the *repetition*: a single touch is not MEDICINE.

Movement is `required` with kind="repeated", so a static "claw over palm" pose fails on movement.
This is the third distinct motion type in the hospital set (HELP=linear, PAIN=converge,
MEDICINE=repeated) — all gated by the same generic verifier, no per-sign logic.

Five-parameter declaration:
  handshape   : dominant "claw" (middle finger toward palm, approx.) over non-dominant "open"
  location    : dominant hand on/over the non-dominant palm           (required)
  movement    : repeated twist/rock about the palm center             (required)
  orientation : non-dominant palm faces up                            (declared, not gated in v1)
  NMM         : none in v1
"""
from __future__ import annotations

from core.schema import HandShapeReq, LocationReq, MovementReq, OrientationReq, Sign

MEDICINE = Sign(
    name="MEDICINE",
    dominant=HandShapeReq(kind="claw", threshold=0.5),       # middle-finger-on-palm shape, coarse bucket
    nondominant=HandShapeReq(kind="open", threshold=0.55),   # flat upward platform palm
    location=LocationReq(anchor="nondominant_palm", max_dist_ratio=0.45, required=True),  # roomy: hands overlap & occlude
    movement=MovementReq(
        kind="repeated",
        actor="dominant",
        reference="nondominant_center",  # the twist oscillates about the supporting palm
        min_cycles=2,                    # at least two back-and-forth rocks
        required=True,
        threshold=0.6,
    ),
    palm_orientation=OrientationReq(facing="up", hand="nondominant", required=False),
)
