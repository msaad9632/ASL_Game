"""Sign Definition Schema — every ASL sign declared as data.

A Sign is a frozen dataclass describing the five linguistic parameters (handshape per hand,
location, movement, palm orientation, non-manual markers), each carrying a `required` flag and
its own confidence threshold. The Phase 3 verifier reads a Sign + a RollingBuffer and gates the
overall pass on EACH required parameter individually — never an average.

Structural guard against the single-frame COFFEE bug (enforced in Sign.__post_init__):
movement is required IF AND ONLY IF a real movement kind is declared. You cannot construct a
sign that:
  - declares a movement (circular/linear/repeated) but marks it not-required (would be ignored), or
  - marks movement required but declares kind = NONE (nothing to check).
So any sign that involves motion MUST be checked over the rolling window. Full stop.

All spatial thresholds are RATIOS of shoulder width (never raw pixels), matching
core.landmarks.normalized_distance, so they hold regardless of camera distance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

# Roles — which physical hand a requirement refers to. The verifier maps these roles to the
# detected Left/Right hands (Phase 3); the schema stays handedness-agnostic.
DOMINANT = "dominant"
NONDOMINANT = "nondominant"


# --------------------------------------------------------------------------- handshape
@dataclass(frozen=True)
class HandShapeReq:
    """Required handshape for one hand, matched by core.handshape predicates."""

    kind: str                       # e.g. "fist" / "S" / "A" / "open"
    required: bool = True
    min_confidence: float = 0.6     # the handshape scorer must clear this to count as a match


# --------------------------------------------------------------------------- location
class Anchor(str, Enum):
    OTHER_HAND = "other_hand"        # position relative to the other hand's center (two-handed)
    NEUTRAL_SPACE = "neutral_space"  # anywhere in the signing space in front of the torso (loose)
    CHEST = "chest"                  # specifically the center of the chest (below the shoulders)
    CHIN = "chin"                    # the hand must REACH chin height (above shoulders) in the window


@dataclass(frozen=True)
class LocationReq:
    """Where the acting hand must be, normalized to shoulder width.

    Two-handed signs typically anchor on OTHER_HAND (e.g. dominant stacked just above the
    non-dominant fist). One-handed signs anchor on NEUTRAL_SPACE.
    """

    anchor: Anchor = Anchor.OTHER_HAND
    acting_hand: str = DOMINANT
    max_dist_ratio: float = 1.0                 # max distance to the anchor, in shoulder-widths
    min_dist_ratio: float = 0.0                 # min distance (keeps hands from fully overlapping)
    vertical: Optional[str] = None              # "above" | "below" (acting vs anchor), or None
    required: bool = True
    min_confidence: float = 0.6


# --------------------------------------------------------------------------- movement
class MovementKind(str, Enum):
    NONE = "none"
    LINEAR = "linear"
    CIRCULAR = "circular"
    REPEATED = "repeated"


@dataclass(frozen=True)
class MovementReq:
    """How the acting hand must move over the rolling window.

    Defaults describe "no movement" (static signs). For a real movement, set `kind` to a
    non-NONE value; the schema then forces `required=True` (see Sign.__post_init__).
    """

    kind: MovementKind = MovementKind.NONE
    actor: str = DOMINANT                       # role whose motion is measured
    pivot: str = NONDOMINANT                    # reference role for circular motion

    # circular
    min_total_rotation_deg: float = 300.0       # |summed unwrapped rotation| about the pivot
    radius_tolerance_ratio: float = 0.4         # allowed radius spread (fraction); rejects wandering

    # linear
    direction: Optional[Tuple[float, float]] = None  # rough (dx, dy), image space (y points down)
    min_displacement_ratio: float = 0.3              # window start->end displacement, shoulder-widths

    # repeated
    min_cycles: int = 2                         # number of back-and-forth cycles

    # shared
    min_duration_s: float = 0.6                 # require this much elapsed motion in the window
    required: bool = True
    min_confidence: float = 0.6


# --------------------------------------------------------------------------- orientation
class PalmFacing(str, Enum):
    IN = "in"
    OUT = "out"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class OrientationReq:
    """Palm-facing requirement for one hand. Off by default (required=False) in v1."""

    hand: str = DOMINANT
    facing: PalmFacing = PalmFacing.DOWN
    required: bool = False
    min_confidence: float = 0.5


# --------------------------------------------------------------------------- sign
@dataclass(frozen=True)
class Sign:
    """A complete declarative description of one ASL sign."""

    name: str
    dominant: HandShapeReq
    location: LocationReq
    movement: MovementReq
    nondominant: Optional[HandShapeReq] = None
    orientation: Optional[OrientationReq] = None
    nmm: None = None                 # non-manual markers — placeholder for v1
    two_handed: bool = True

    def __post_init__(self):
        # The structural guard. Movement is required IFF a real kind is declared.
        has_motion = self.movement.kind != MovementKind.NONE
        if has_motion and not self.movement.required:
            raise ValueError(
                f"Sign '{self.name}': declares movement kind={self.movement.kind.value} but "
                f"movement.required=False. A declared movement must be enforced - otherwise the "
                f"sign could pass with no motion (the single-frame COFFEE bug). Set required=True."
            )
        if self.movement.required and not has_motion:
            raise ValueError(
                f"Sign '{self.name}': movement.required=True but kind=NONE - nothing to verify. "
                f"Give it a real movement kind (linear/circular/repeated), or mark it not required."
            )
        if self.two_handed and self.nondominant is None:
            raise ValueError(
                f"Sign '{self.name}': two_handed=True but no nondominant handshape was given."
            )

    def required_parameters(self) -> list[str]:
        """Stable parameter keys the verifier must individually clear for an overall pass."""
        params: list[str] = []
        if self.dominant.required:
            params.append("handshape_dominant")
        if self.nondominant is not None and self.nondominant.required:
            params.append("handshape_nondominant")
        if self.location.required:
            params.append("location")
        if self.movement.required:
            params.append("movement")
        if self.orientation is not None and self.orientation.required:
            params.append("orientation")
        return params
