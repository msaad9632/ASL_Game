import { clip, unwrapAngles } from './math-utils';
import { MovementKind, type MovementReq } from './schema';

type Traj = [number, number[]][]; // (t, center)[]

const RADIUS_CV_FREE = 0.30;

function series(traj: Traj): { ts: number[]; pts: number[][] } {
  const ts = traj.map(([t]) => t);
  const pts = traj.map(([, c]) => [...c]);
  return { ts, pts };
}

function norm2dArr(pts: number[][]): number[] {
  return pts.map((p) => Math.sqrt(p[0] * p[0] + p[1] * p[1]));
}

function meanPt(pts: number[][]): number[] {
  const n = pts.length;
  if (n === 0) return [0, 0];
  let sx = 0, sy = 0;
  for (const p of pts) { sx += p[0]; sy += p[1]; }
  return [sx / n, sy / n];
}

function arrMean(a: number[]): number {
  if (a.length === 0) return 0;
  let s = 0;
  for (const v of a) s += v;
  return s / a.length;
}

function arrStd(a: number[]): number {
  if (a.length === 0) return 0;
  const m = arrMean(a);
  let s = 0;
  for (const v of a) s += (v - m) * (v - m);
  return Math.sqrt(s / a.length);
}

export interface CircularMetrics {
  score: number;
  netRotationDeg: number;
  radiusCv: number;
  meanRRatio: number;
  n: number;
  duration: number;
}

export function circularMetrics(
  actorTraj: Traj,
  shoulderWidth: number,
  req: MovementReq
): CircularMetrics {
  const n = actorTraj.length;
  if (n < 5 || !shoulderWidth || shoulderWidth <= 0) {
    return { score: 0, netRotationDeg: 0, radiusCv: 99, meanRRatio: 0, n, duration: 0 };
  }

  const { ts, pts } = series(actorTraj);
  const duration = ts[ts.length - 1] - ts[0];
  const pivot = meanPt(pts);
  const rel = pts.map((p) => [p[0] - pivot[0], p[1] - pivot[1]]);
  const radii = norm2dArr(rel);
  const meanR = arrMean(radii);
  const meanRRatio = meanR / shoulderWidth;
  const rawAngles = rel.map((r) => Math.atan2(r[1], r[0]));
  const angles = unwrapAngles(rawAngles);
  const netRotation = Math.abs((angles[angles.length - 1] - angles[0]) * 180 / Math.PI);
  const radiusCv = meanR > 1e-6 ? arrStd(radii) / meanR : 99;

  if (duration < req.minDurationS || meanRRatio < 0.03) {
    return { score: 0, netRotationDeg: netRotation, radiusCv, meanRRatio, n, duration };
  }

  const rotationScore = clip(netRotation / req.minTotalRotationDeg, 0, 1);
  const radiusExcess = Math.max(0, radiusCv - RADIUS_CV_FREE);
  const radiusScore = clip(1.0 - radiusExcess / Math.max(req.radiusToleranceRatio, 1e-6), 0, 1);
  const score = rotationScore * radiusScore;

  return { score, netRotationDeg: netRotation, radiusCv, meanRRatio, n, duration };
}

export function circularConfidence(actorTraj: Traj, shoulderWidth: number, req: MovementReq): number {
  return circularMetrics(actorTraj, shoulderWidth, req).score;
}

export function linearConfidence(actorTraj: Traj, shoulderWidth: number, req: MovementReq): number {
  if (actorTraj.length < 3 || !shoulderWidth || shoulderWidth <= 0) return 0;
  const { ts, pts } = series(actorTraj);
  if (ts[ts.length - 1] - ts[0] < req.minDurationS) return 0;

  const disp = [pts[pts.length - 1][0] - pts[0][0], pts[pts.length - 1][1] - pts[0][1]];
  const mag = Math.sqrt(disp[0] * disp[0] + disp[1] * disp[1]);
  const magRatio = mag / shoulderWidth;
  if (magRatio < 0.05) return 0;
  const magScore = clip(magRatio / req.minDisplacementRatio, 0, 1);

  let dirScore = 1.0;
  if (req.direction) {
    const dn = Math.sqrt(req.direction[0] ** 2 + req.direction[1] ** 2);
    if (dn > 1e-6 && mag > 1e-6) {
      const unit = [disp[0] / mag, disp[1] / mag];
      const nd = [req.direction[0] / dn, req.direction[1] / dn];
      dirScore = clip(unit[0] * nd[0] + unit[1] * nd[1], 0, 1);
    }
  }

  return magScore * dirScore;
}

export function repeatedConfidence(actorTraj: Traj, shoulderWidth: number, req: MovementReq): number {
  if (actorTraj.length < 6 || !shoulderWidth || shoulderWidth <= 0) return 0;
  const { ts, pts } = series(actorTraj);
  if (ts[ts.length - 1] - ts[0] < req.minDurationS) return 0;

  const centroid = meanPt(pts);
  const signal = pts.map((p) => Math.sqrt((p[0] - centroid[0]) ** 2 + (p[1] - centroid[1]) ** 2));

  const sigMin = Math.min(...signal);
  const sigMax = Math.max(...signal);
  const ampFloor = Math.max(req.minAmplitudeRatio, 1e-6);
  const ampRatio = (sigMax - sigMin) / shoulderWidth;
  if (ampRatio < ampFloor) return 0;

  const sigMean = arrMean(signal);
  const centered = signal.map((v) => v - sigMean);
  const maxAbs = Math.max(...centered.map(Math.abs));
  const noise = 0.25 * maxAbs;
  let crossings = 0;
  let last = 0;
  for (const v of centered) {
    if (Math.abs(v) < noise) continue;
    const cur = v > 0 ? 1 : -1;
    if (last !== 0 && cur !== last) crossings++;
    last = cur;
  }
  const cycles = crossings / 2;

  const cycleScore = clip(cycles / Math.max(req.minCycles, 1), 0, 1);
  const ampScore = clip(ampRatio / (ampFloor * 1.6), 0, 1);
  return Math.min(cycleScore, ampScore);
}

export function convergeConfidence(
  trajA: Traj,
  trajB: Traj,
  shoulderWidth: number,
  req: MovementReq
): number {
  const n = Math.min(trajA.length, trajB.length);
  if (n < 3 || shoulderWidth <= 0) return 0;

  const ts = trajA.slice(0, n).map(([t]) => t);
  if (ts[ts.length - 1] - ts[0] < req.minDurationS) return 0;

  const gap = [];
  for (let i = 0; i < n; i++) {
    const dx = trajA[i][1][0] - trajB[i][1][0];
    const dy = trajA[i][1][1] - trajB[i][1][1];
    gap.push(Math.sqrt(dx * dx + dy * dy) / shoulderWidth);
  }

  const k = Math.max(1, Math.floor(n / 4));
  const startGap = arrMean(gap.slice(0, k));
  const endGap = arrMean(gap.slice(n - k));
  const approach = startGap - endGap;

  let mono = 0;
  if (n > 1) {
    let dec = 0;
    for (let i = 1; i < gap.length; i++) {
      if (gap[i] < gap[i - 1]) dec++;
    }
    mono = dec / (gap.length - 1);
  }

  let magScore: number;
  if (req.minApproachRatio > 0) {
    magScore = clip(approach / req.minApproachRatio, 0, 1);
  } else {
    magScore = approach > 0 ? 1 : 0;
  }

  return clip(magScore * (0.5 + 0.5 * mono), 0, 1);
}

export function movementConfidence(actorTraj: Traj, shoulderWidth: number, req: MovementReq): number {
  if (req.kind === MovementKind.NONE) return 1.0;
  if (req.kind === MovementKind.CIRCULAR) return circularConfidence(actorTraj, shoulderWidth, req);
  if (req.kind === MovementKind.LINEAR) return linearConfidence(actorTraj, shoulderWidth, req);
  if (req.kind === MovementKind.REPEATED) return repeatedConfidence(actorTraj, shoulderWidth, req);
  return 0;
}
