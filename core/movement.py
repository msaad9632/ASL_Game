"""Movement detectors over the rolling buffer — the core of the anti-bug fix.

Implemented in Phase 3.
  - circular: per-frame atan2 angle of the acting hand about a pivot, unwrapped and summed;
    passes only if total rotation clears threshold AND radius stays within a tolerance band
    (the radius check rejects "hand wandered randomly" as a false circle).
  - linear: displacement vector window-start->end; direction, magnitude, monotonic progression.
  - repeated: periodicity (cycle count) in the distance/velocity curve.
"""
