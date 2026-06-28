"""Fingerspelled letter L — index up + thumb out (an 'L' shape), held still."""
from core.schema import DOMINANT, Anchor, HandShapeReq, LocationReq, MovementKind, MovementReq, Sign

LETTER_L = Sign(
    name="LETTER_L",
    two_handed=False,
    dominant=HandShapeReq(kind="l", required=True),
    nondominant=None,
    location=LocationReq(anchor=Anchor.NEUTRAL_SPACE, acting_hand=DOMINANT, max_dist_ratio=3.0, required=False),
    movement=MovementReq(kind=MovementKind.NONE, required=False),
)
