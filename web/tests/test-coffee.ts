import { describe, it, expect } from 'vitest';
import { RollingBuffer, frameFromDict } from '../src/engine/landmarks';
import { verify, resultPassed, resultGet, paramCleared } from '../src/engine/verifier';
import { COFFEE } from '../src/engine/signs/coffee';
import correctFixture from './fixtures/coffee_correct.json';
import confusorFixture from './fixtures/coffee_confusor.json';

function loadBuffer(fixture: { frames: unknown[] }): RollingBuffer {
  const buf = new RollingBuffer(2.0);
  for (const fd of fixture.frames) {
    buf.add(frameFromDict(fd as Parameters<typeof frameFromDict>[0]));
  }
  return buf;
}

describe('COFFEE correct', () => {
  const buffer = loadBuffer(correctFixture);
  const result = verify(buffer, COFFEE);

  it('passes overall', () => {
    expect(resultPassed(result)).toBe(true);
  });

  it('movement clears threshold', () => {
    const movement = resultGet(result, 'movement')!;
    expect(movement).toBeDefined();
    expect(paramCleared(movement)).toBe(true);
  });

  it('handshape clears', () => {
    const dom = resultGet(result, 'handshape_dominant')!;
    expect(dom).toBeDefined();
    expect(paramCleared(dom)).toBe(true);
  });
});

describe('COFFEE confusor (static fists, no motion)', () => {
  const buffer = loadBuffer(confusorFixture);
  const result = verify(buffer, COFFEE);

  it('fails overall', () => {
    expect(resultPassed(result)).toBe(false);
  });

  it('fails on movement specifically', () => {
    const movement = resultGet(result, 'movement')!;
    expect(movement).toBeDefined();
    expect(paramCleared(movement)).toBe(false);
  });

  it('movement score below threshold', () => {
    const movement = resultGet(result, 'movement')!;
    expect(movement.score).toBeLessThan(movement.threshold);
  });

  it('handshape is still good', () => {
    const dom = resultGet(result, 'handshape_dominant')!;
    expect(paramCleared(dom)).toBe(true);
  });
});
