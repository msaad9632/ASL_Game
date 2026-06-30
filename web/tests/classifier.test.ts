import { describe, it, expect } from 'vitest';
import type { ClassifierVote } from '../src/engine/gate';
import { topK as topKImpl } from '../src/engine/classifier';

const vote: ClassifierVote = {
  topSign: 'COFFEE',
  confidence: 0.7,
  perSign: { COFFEE: 0.7, TEA: 0.2, WATER: 0.07, MILK: 0.03 },
};

describe('topK', () => {
  it('returns the k highest predictions, highest first', () => {
    const t = topKImpl(vote, 2);
    expect(t).toEqual([
      { sign: 'COFFEE', prob: 0.7 },
      { sign: 'TEA', prob: 0.2 },
    ]);
  });

  it('clamps k to the number of classes', () => {
    expect(topKImpl(vote, 99)).toHaveLength(4);
  });
});
