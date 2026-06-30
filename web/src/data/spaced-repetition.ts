import type { SignStats } from '@/types/user';

export function getSignsDueForReview(
  signAccuracy: Record<string, SignStats>,
  limit = 10
): string[] {
  const now = Date.now();
  const due = Object.entries(signAccuracy)
    .filter(([, stats]) => stats.nextReviewAt <= now)
    .sort(([, a], [, b]) => a.nextReviewAt - b.nextReviewAt)
    .map(([id]) => id);

  if (due.length >= limit) return due.slice(0, limit);

  const weakest = Object.entries(signAccuracy)
    .filter(([id]) => !due.includes(id))
    .sort(([, a], [, b]) => {
      const aRate = a.attempts > 0 ? a.successes / a.attempts : 0;
      const bRate = b.attempts > 0 ? b.successes / b.attempts : 0;
      return aRate - bRate;
    })
    .map(([id]) => id);

  return [...due, ...weakest].slice(0, limit);
}

export function pickReceptiveDistractors(
  correctId: string,
  allSignIds: string[],
  count = 3
): string[] {
  const pool = allSignIds.filter((id) => id !== correctId);
  const shuffled = pool.sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}
