"""Frame model, rolling buffer, and shoulder-width normalization.

Implemented in Phase 1. Will define:
  - Frame: one timestamped sample (21 landmarks/hand + pose shoulder points).
  - RollingBuffer: a fixed ~1.5-2s time window of Frames (the basis for all movement checks).
  - normalization helpers that express every distance as a ratio of shoulder width, so
    thresholds don't break when the user sits closer to or further from the camera.
"""
