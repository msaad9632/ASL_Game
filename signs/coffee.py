"""COFFEE sign definition.

COFFEE = both hands in an S-handshape (a closed fist). The dominant fist circles (grinds) on
top of a stationary non-dominant fist, like grinding coffee beans. Movement is REQUIRED — this
is the sign whose single-frame check caused the original bug, so its definition is the canonical
proof that the schema now forces motion to be verified.

Parameters declared:
  - handshape (both hands): fist          [required]
  - location: dominant stacked just above the non-dominant fist, close together   [required]
  - movement: dominant circles about the non-dominant fist, >= ~300 deg total     [required]
  - orientation: dominant palm roughly down (grinding on top)                     [not required in v1]
"""
from core.schema import (
    DOMINANT,
    NONDOMINANT,
    Anchor,
    HandShapeReq,
    LocationReq,
    MovementKind,
    MovementReq,
    OrientationReq,
    PalmFacing,
    Sign,
)

COFFEE = Sign(
    name="COFFEE",
    two_handed=True,
    dominant=HandShapeReq(kind="fist", required=True),
    nondominant=HandShapeReq(kind="fist", required=True),
    location=LocationReq(
        anchor=Anchor.OTHER_HAND,
        acting_hand=DOMINANT,
        max_dist_ratio=0.6,      # stacked / close: within ~0.6 shoulder-widths of the other fist
        min_dist_ratio=0.0,
        vertical="above",        # dominant fist sits above the non-dominant fist
        required=True,
    ),
    movement=MovementReq(
        kind=MovementKind.CIRCULAR,
        actor=DOMINANT,
        pivot=NONDOMINANT,
        min_total_rotation_deg=270.0,   # ~3/4 turn of accumulated rotation
        radius_tolerance_ratio=0.6,     # forgiving radius band for a real (imperfect) grind
        min_duration_s=0.6,
        required=True,
    ),
    # Real-world COFFEE has the dominant palm facing down; left non-gating in v1 until the
    # orientation scorer is reliable.
    orientation=OrientationReq(hand=DOMINANT, facing=PalmFacing.DOWN, required=False),
)
