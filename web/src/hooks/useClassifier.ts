import { useEffect, useState, useCallback } from 'react';
import { loadClassifier, type SignClassifier } from '@/engine/classifier';
import type { GateDecision } from '@/engine/gate';
import { MODEL_URL, CLASSES_URL, CLASSIFIER_DEBUG } from '@/config/classifier';

export type ClassifierStatus = 'disabled' | 'loading' | 'ready';

interface LoadResult {
  classifier: SignClassifier | null;
  status: ClassifierStatus;
}

// Module-level cache so the (potentially multi-MB) model loads ONCE for the whole app,
// not once per page mount.
let cached: Promise<LoadResult> | null = null;

async function fetchClasses(): Promise<string[] | null> {
  try {
    const res = await fetch(CLASSES_URL);
    if (!res.ok) return null; // no model deployed -> silently disabled
    const data = await res.json();
    return Array.isArray(data) ? (data as string[]) : null;
  } catch {
    return null;
  }
}

function loadOnce(): Promise<LoadResult> {
  if (!cached) {
    cached = (async () => {
      const classes = await fetchClasses();
      if (!classes) return { classifier: null, status: 'disabled' as const };
      const c = await loadClassifier(MODEL_URL, classes);
      return c.enabled
        ? { classifier: c, status: 'ready' as const }
        : { classifier: null, status: 'disabled' as const };
    })();
  }
  return cached;
}

/**
 * Loads the optional TF.js disambiguation model (once, app-wide) and returns a ready-made
 * decision logger. Always safe: if no model is deployed, `classifier` is null and the app
 * runs on the rule verifier alone.
 *
 *   const { classifier, status, logVote } = useClassifier();
 *   const recognition = useRecognition({ onPass, classifier, onVote: logVote });
 */
export function useClassifier() {
  const [state, setState] = useState<LoadResult>({ classifier: null, status: 'loading' });

  useEffect(() => {
    let active = true;
    loadOnce().then((r) => {
      if (!active) return;
      setState(r);
      if (CLASSIFIER_DEBUG) {
        console.log(`[classifier] ${r.status}${r.status === 'ready' ? ' — disambiguation active' : ''}`);
      }
    });
    return () => { active = false; };
  }, []);

  // Gated debug logger for gate decisions. Stable identity across renders.
  const logVote = useCallback((d: GateDecision) => {
    if (!CLASSIFIER_DEBUG) return;
    const tk = d.topK.map((t) => `${t.sign} ${(t.prob * 100).toFixed(0)}%`).join('  ');
    const tag = d.decision === 'pass' ? 'PASS ✓' : 'VETO ✗';
    console.log(`[classifier] ${tag}  prompt=${d.prompted}  top: ${tk}${d.hint ? `  hint="${d.hint}"` : ''}`);
    (window as unknown as { __lastVote?: GateDecision }).__lastVote = d;
  }, []);

  return { classifier: state.classifier, status: state.status, logVote };
}
