import { useRef, useState, useCallback, useEffect } from 'react';
import { Capture } from '@/engine/capture';
import { RollingBuffer, HandStabilizer } from '@/engine/landmarks';
import { verify, type VerifyResult, resultPassed } from '@/engine/verifier';
import type { Sign } from '@/engine/schema';

export type RecognitionStatus = 'loading' | 'ready' | 'running' | 'error';

interface UseRecognitionOpts {
  onPass?: (result: VerifyResult) => void;
}

export function useRecognition(opts?: UseRecognitionOpts) {
  const captureRef = useRef<Capture | null>(null);
  const bufferRef = useRef(new RollingBuffer(2.0));
  const stabilizerRef = useRef(new HandStabilizer(0.3));
  const rafRef = useRef<number>(0);
  const signRef = useRef<Sign | null>(null);
  const runningRef = useRef(false);
  const [status, setStatus] = useState<RecognitionStatus>('loading');
  const [result, setResult] = useState<VerifyResult | null>(null);
  const passCallbackRef = useRef(opts?.onPass);
  passCallbackRef.current = opts?.onPass;
  const frameCountRef = useRef(0);

  const init = useCallback(async () => {
    if (captureRef.current?.ready) {
      setStatus('ready');
      return;
    }
    setStatus('loading');
    try {
      const cap = new Capture();
      await cap.init();
      captureRef.current = cap;
      console.log('[SignUp] MediaPipe initialized');
      setStatus('ready');
    } catch (e) {
      console.error('[SignUp] MediaPipe init failed:', e);
      setStatus('error');
    }
  }, []);

  const startLoop = useCallback(
    (video: HTMLVideoElement, sign: Sign) => {
      // Always stop previous loop first
      cancelAnimationFrame(rafRef.current);
      runningRef.current = false;

      signRef.current = sign;
      bufferRef.current.clear();
      stabilizerRef.current.reset();
      setResult(null);
      frameCountRef.current = 0;

      const cap = captureRef.current;
      if (!cap?.ready) {
        console.warn('[SignUp] Capture not ready, cannot start loop');
        return;
      }

      runningRef.current = true;
      setStatus('running');
      console.log('[SignUp] Loop started for', sign.name);

      // Require buffer to fill (~1.5s) before allowing a pass.
      // This prevents instant passes on static signs and gives
      // movement signs time to accumulate trajectory data.
      const MIN_FRAMES_BEFORE_PASS = 30;
      let passFrames = 0;
      const PASS_THRESHOLD = 6;

      const tick = () => {
        if (!runningRef.current || !signRef.current) return;

        if (video.readyState < 2) {
          rafRef.current = requestAnimationFrame(tick);
          return;
        }

        try {
          const tsMs = performance.now();
          let frame = cap.process(video, Math.round(tsMs));
          frame = stabilizerRef.current.stabilize(frame);
          bufferRef.current.add(frame);
          frameCountRef.current++;

          const vr = verify(bufferRef.current, signRef.current);
          setResult(vr);

          // Log first few frames for debugging
          if (frameCountRef.current <= 3) {
            const hands = frame.hands.length;
            const sw = frame.leftShoulder && frame.rightShoulder ? 'yes' : 'no';
            console.log(`[SignUp] Frame ${frameCountRef.current}: hands=${hands} shoulders=${sw} w=${frame.width}`);
          }

          // Don't allow pass until buffer has enough data
          if (frameCountRef.current >= MIN_FRAMES_BEFORE_PASS && resultPassed(vr)) {
            passFrames++;
            if (passFrames >= PASS_THRESHOLD) {
              console.log('[SignUp] PASS:', sign.name, vr.params.map(p => `${p.name}=${p.score.toFixed(2)}`).join(' '));
              passCallbackRef.current?.(vr);
              passFrames = 0;
            }
          } else {
            passFrames = 0;
          }
        } catch (e) {
          console.error('[SignUp] Tick error:', e);
        }

        if (runningRef.current) {
          rafRef.current = requestAnimationFrame(tick);
        }
      };

      rafRef.current = requestAnimationFrame(tick);
    },
    []
  );

  const stopLoop = useCallback(() => {
    runningRef.current = false;
    cancelAnimationFrame(rafRef.current);
    signRef.current = null;
    setStatus((s) => (s === 'running' ? 'ready' : s));
  }, []);

  const setSign = useCallback((sign: Sign) => {
    signRef.current = sign;
    bufferRef.current.clear();
    stabilizerRef.current.reset();
    frameCountRef.current = 0;
    setResult(null);
  }, []);

  useEffect(() => {
    return () => {
      runningRef.current = false;
      cancelAnimationFrame(rafRef.current);
      captureRef.current?.close();
    };
  }, []);

  return { status, result, init, startLoop, stopLoop, setSign };
}
