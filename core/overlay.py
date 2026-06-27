"""Dev-only debug overlay — live per-parameter scores.

Draws the verifier's per-parameter breakdown so failures are explainable, not guessed:
green = cleared its threshold, red = required and below, gray = optional (doesn't block).
Used behind a --debug flag by scenarios and demos.
"""
from __future__ import annotations

import cv2
import numpy as np


def draw_param_scores(img, result, movement_dbg: str = "", y0: int = 28) -> None:
    x, y, line = 12, y0, 27
    banner = "PASS" if result.passed else "..."
    color = (0, 200, 0) if result.passed else (0, 165, 255)
    cv2.putText(img, f"{result.sign_name}: {banner}", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    y += 30
    for p in result.params:
        if p.cleared:
            col = (0, 200, 0)
        elif p.required:
            col = (0, 0, 255)
        else:
            col = (130, 130, 130)
        bar = int(np.clip(p.score, 0.0, 1.0) * 120)
        cv2.rectangle(img, (x, y - 12), (x + 120, y), (70, 70, 70), 1)
        cv2.rectangle(img, (x, y - 12), (x + bar, y), col, -1)
        tag = "req" if p.required else "opt"
        tcol = (255, 255, 255) if p.required else (150, 150, 150)
        cv2.putText(img, f"{p.name:<22}{p.score:0.2f}/{p.threshold:0.2f} [{tag}]",
                    (x + 128, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, tcol, 1, cv2.LINE_AA)
        y += line
    if movement_dbg:
        cv2.putText(img, movement_dbg, (x, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
