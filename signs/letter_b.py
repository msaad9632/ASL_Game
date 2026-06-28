"""Fingerspelled letter B — flat open hand held still (handshape only)."""
from core.schema import DOMINANT, Anchor, HandShapeReq, LocationReq, MovementKind, MovementReq, Sign

LETTER_B = Sign(
    name="LETTER_B",
    two_handed=False,
    dominant=HandShapeReq(kind="b", required=True),
    nondominant=None,
    location=LocationReq(anchor=Anchor.NEUTRAL_SPACE, acting_hand=DOMINANT, max_dist_ratio=3.0, required=False),
    movement=MovementReq(kind=MovementKind.NONE, required=False),
)
