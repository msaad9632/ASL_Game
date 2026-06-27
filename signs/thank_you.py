"""THANK YOU sign definition.

THANK YOU = a flat/open hand starting at the chin/lips, moving forward and DOWN toward the
person. From a front-facing webcam the reliable 2D signal is the downward motion (the forward
component is along the camera axis and barely visible in 2D), so movement is a downward LINEAR
motion. Location is left non-required because the hand travels through space (chin -> out); the
distinguishing parameters are the open handshape + the downward movement.

Parameters declared:
  - handshape (dominant): open / flat hand     [required]
  - movement: linear, downward                 [required]
  - location: not gated (the hand moves)       [not required]
  - orientation: palm up-ish                   [not required in v1]
"""
from core.schema import (
    DOMINANT,
    Anchor,
    HandShapeReq,
    LocationReq,
    MovementKind,
    MovementReq,
    OrientationReq,
    PalmFacing,
    Sign,
)

THANK_YOU = Sign(
    name="THANK_YOU",
    two_handed=False,
    dominant=HandShapeReq(kind="open", required=True),
    nondominant=None,
    location=LocationReq(
        anchor=Anchor.NEUTRAL_SPACE,
        acting_hand=DOMINANT,
        max_dist_ratio=2.5,      # very loose; the hand moves through space, so don't gate it
        required=False,
    ),
    movement=MovementReq(
        kind=MovementKind.LINEAR,
        actor=DOMINANT,
        direction=(0.0, 1.0),            # downward in image space (y grows downward)
        min_displacement_ratio=0.3,      # at least ~0.3 shoulder-widths of travel
        min_duration_s=0.4,
        required=True,
    ),
    orientation=OrientationReq(hand=DOMINANT, facing=PalmFacing.UP, required=False),
)
