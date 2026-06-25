"""Geometric handshape predicates (fist / S / A / ...).

Implemented in Phase 3. Pure-geometry classifiers over a single hand's 21 landmarks, smoothed
across recent frames by majority vote / moving average so one noisy frame can't flip the result.
Note: A vs S vs plain fist are a minimal pair distinguished only by thumb position.
"""
