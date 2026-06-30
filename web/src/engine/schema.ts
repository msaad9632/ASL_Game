export const DOMINANT = 'dominant' as const;
export const NONDOMINANT = 'nondominant' as const;
export type Role = typeof DOMINANT | typeof NONDOMINANT;

export interface HandShapeReq {
  kind: string;
  required: boolean;
  minConfidence: number;
}

export enum Anchor {
  OTHER_HAND = 'other_hand',
  NEUTRAL_SPACE = 'neutral_space',
  CHEST = 'chest',
  CHIN = 'chin',
  FOREHEAD = 'forehead',
  BELLY = 'belly',
  SHOULDER = 'shoulder',
}

export interface LocationReq {
  anchor: Anchor;
  actingHand: Role;
  maxDistRatio: number;
  minDistRatio: number;
  vertical?: 'above' | 'below' | null;
  below?: 'mouth' | null;
  useClosestApproach: boolean;
  required: boolean;
  minConfidence: number;
}

export enum MovementKind {
  NONE = 'none',
  LINEAR = 'linear',
  CIRCULAR = 'circular',
  REPEATED = 'repeated',
  CONVERGE = 'converge',
}

export interface MovementReq {
  kind: MovementKind;
  actor: Role;
  pivot: Role;
  minTotalRotationDeg: number;
  radiusToleranceRatio: number;
  direction?: [number, number] | null;
  minDisplacementRatio: number;
  minCycles: number;
  minAmplitudeRatio: number;
  minApproachRatio: number;
  minDurationS: number;
  required: boolean;
  minConfidence: number;
}

export enum PalmFacing {
  IN = 'in',
  OUT = 'out',
  UP = 'up',
  DOWN = 'down',
  LEFT = 'left',
  RIGHT = 'right',
}

export interface OrientationReq {
  hand: Role;
  facing: PalmFacing;
  required: boolean;
  minConfidence: number;
}

export interface Sign {
  name: string;
  dominant: HandShapeReq;
  location: LocationReq;
  movement: MovementReq;
  nondominant?: HandShapeReq;
  orientation?: OrientationReq;
  twoHanded: boolean;
}

export function createSign(opts: {
  name: string;
  dominant: Partial<HandShapeReq> & { kind: string };
  location: Partial<LocationReq>;
  movement?: Partial<MovementReq>;
  nondominant?: Partial<HandShapeReq> & { kind: string };
  orientation?: Partial<OrientationReq>;
  twoHanded?: boolean;
}): Sign {
  const movement: MovementReq = {
    kind: MovementKind.NONE,
    actor: DOMINANT,
    pivot: NONDOMINANT,
    minTotalRotationDeg: 300,
    radiusToleranceRatio: 0.4,
    direction: null,
    minDisplacementRatio: 0.3,
    minCycles: 2,
    minAmplitudeRatio: 0.05,
    minApproachRatio: 0.15,
    minDurationS: 0.6,
    required: true,
    minConfidence: 0.6,
    ...opts.movement,
  };

  const hasMotion = movement.kind !== MovementKind.NONE;
  if (hasMotion && !movement.required) {
    throw new Error(
      `Sign '${opts.name}': declares movement kind=${movement.kind} but required=false.`
    );
  }
  if (movement.required && !hasMotion) {
    throw new Error(
      `Sign '${opts.name}': movement.required=true but kind=NONE.`
    );
  }

  const twoHanded = opts.twoHanded ?? true;
  if (twoHanded && !opts.nondominant) {
    throw new Error(
      `Sign '${opts.name}': twoHanded=true but no nondominant handshape given.`
    );
  }

  const sign: Sign = {
    name: opts.name,
    twoHanded,
    dominant: { required: true, minConfidence: 0.6, ...opts.dominant },
    location: {
      anchor: Anchor.OTHER_HAND,
      actingHand: DOMINANT,
      maxDistRatio: 1.0,
      minDistRatio: 0.0,
      vertical: null,
      below: null,
      useClosestApproach: false,
      required: true,
      minConfidence: 0.6,
      ...opts.location,
    },
    movement,
  };

  if (opts.nondominant) {
    sign.nondominant = { required: true, minConfidence: 0.6, ...opts.nondominant };
  }
  if (opts.orientation) {
    sign.orientation = {
      hand: DOMINANT,
      facing: PalmFacing.DOWN,
      required: false,
      minConfidence: 0.5,
      ...opts.orientation,
    };
  }

  return sign;
}
