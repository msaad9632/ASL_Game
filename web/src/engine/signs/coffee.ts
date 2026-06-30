import { createSign, Anchor, MovementKind, PalmFacing, DOMINANT, NONDOMINANT } from '../schema';

export const COFFEE = createSign({
  name: 'COFFEE',
  twoHanded: true,
  dominant: { kind: 'fist', required: true, minConfidence: 0.5 },
  nondominant: { kind: 'fist', required: true, minConfidence: 0.5 },
  location: {
    anchor: Anchor.OTHER_HAND,
    actingHand: DOMINANT,
    maxDistRatio: 0.9,
    minDistRatio: 0.0,
    vertical: 'above',
    required: true,
  },
  movement: {
    kind: MovementKind.CIRCULAR,
    actor: DOMINANT,
    pivot: NONDOMINANT,
    minTotalRotationDeg: 360.0,
    radiusToleranceRatio: 1.0,
    minDurationS: 0.6,
    required: true,
  },
  orientation: { hand: DOMINANT, facing: PalmFacing.DOWN, required: false },
});
