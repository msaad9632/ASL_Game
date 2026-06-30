/**
 * Disambiguation gate — combines the rule verifier's pass with the ML classifier's vote.
 *
 * Design invariant: the rule verifier remains authoritative for the per-parameter Sign Coach.
 * The classifier NEVER overrides a rule failure into a pass; it can only ADD a veto (reject a
 * rule-pass when the model is confident the user signed something else) and an optional hint.
 * When the classifier is disabled (no model loaded), behavior is exactly today's: rules alone.
 */

export interface ClassifierVote {
  /** Highest-probability sign id. */
  topSign: string;
  /** Probability of topSign, 0..1. */
  confidence: number;
  /** Probability per sign id (only the game vocabulary needs to be present). */
  perSign: Record<string, number>;
}

/** Full record of one gate decision — emitted to onVote for logging/debug overlays. */
export interface GateDecision {
  /** The sign the user was asked to make. */
  prompted: string;
  /** The classifier's raw vote (null if it produced nothing for this window). */
  vote: ClassifierVote | null;
  /** Whether the rule-pass survived the gate. */
  decision: 'pass' | 'veto';
  /** Top predictions, highest first. */
  topK: { sign: string; prob: number }[];
  /** Coaching hint when the model confidently saw a different sign. */
  hint: string | null;
}

/**
 * Final pass decision. Requires the rule verifier to pass AND — when a classifier vote is
 * present — the classifier's probability for the PROMPTED sign to clear `minConfidence`.
 * This kills false positives the rules miss (e.g. a confusor that satisfies the loose rules
 * but that the model recognizes as a different sign).
 */
export function gatePass(
  rulePassed: boolean,
  vote: ClassifierVote | null,
  promptedSign: string,
  minConfidence = 0.5
): boolean {
  if (!rulePassed) return false;
  if (!vote) return true; // classifier disabled -> rules alone (unchanged behavior)
  const conf = vote.perSign[promptedSign] ?? 0;
  return conf >= minConfidence;
}

/**
 * Additive coaching hint shown next to (never replacing) the Sign Coach checklist. Returns a
 * message only when the model is confidently pointing at a DIFFERENT sign than the prompt.
 */
export function gateHint(
  vote: ClassifierVote | null,
  promptedSign: string,
  hintConfidence = 0.6
): string | null {
  if (!vote) return null;
  if (vote.topSign !== promptedSign && vote.confidence >= hintConfidence) {
    return `That looked more like ${vote.topSign.replace(/_/g, ' ')} — check the reference.`;
  }
  return null;
}
