"""Fingerspelled letter Y — thumb + pinky out, three middle fingers curled, held still."""
from core.schema import DOMINANT, Anchor, HandShapeReq, LocationReq, MovementKind, MovementReq, Sign

LETTER_Y = Sign(
    name="LETTER_Y",
    two_handed=False,
    dominant=HandShapeReq(kind="y", required=True),
    nondominant=None,
    location=LocationReq(anchor=Anchor.NEUTRAL_SPACE, acting_hand=DOMINANT, max_dist_ratio=3.0, required=False),
    movement=MovementReq(kind=MovementKind.NONE, required=False),
)
