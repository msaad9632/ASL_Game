import { cross3d, dot, vecNorm, clip } from './math-utils';
import type { Hand } from './landmarks';
import { WRIST, INDEX_MCP, PINKY_MCP } from './landmarks';
import { PalmFacing } from './schema';

const TARGETS: Record<PalmFacing, [number, number, number]> = {
  [PalmFacing.DOWN]: [0, 1, 0],
  [PalmFacing.UP]: [0, -1, 0],
  [PalmFacing.RIGHT]: [1, 0, 0],
  [PalmFacing.LEFT]: [-1, 0, 0],
  [PalmFacing.IN]: [0, 0, 1],
  [PalmFacing.OUT]: [0, 0, -1],
};

export function palmNormal(hand: Hand): [number, number, number] {
  const w = hand.points[WRIST];
  const i = hand.points[INDEX_MCP];
  const p = hand.points[PINKY_MCP];
  const v1 = [i[0] - w[0], i[1] - w[1], i[2] - w[2]] as [number, number, number];
  const v2 = [p[0] - w[0], p[1] - w[1], p[2] - w[2]] as [number, number, number];
  const n = cross3d(v1, v2);
  const len = vecNorm(n);
  return len > 1e-6 ? [n[0] / len, n[1] / len, n[2] / len] : n;
}

export function facingConfidence(hand: Hand, facing: PalmFacing): number {
  const n = palmNormal(hand);
  const t = TARGETS[facing];
  return clip(dot(n, t), 0, 1);
}
