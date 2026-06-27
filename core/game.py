"""Shared game mechanics, theme-agnostic — reused by every scenario.

Picture-in-picture webcam compositor, prompt banner, score HUD, and a flash overlay. Each
scenario supplies its own background/theme but reuses these so the coffee-shop and hospital
scenarios feel consistent without duplicating UI code.
"""
from __future__ import annotations

import cv2
import numpy as np


def composite_pip(canvas, cam_bgr, scale: float = 0.3, margin: int = 24,
                  border=(255, 255, 255), label: str = "you"):
    """Overlay the webcam as a bordered picture-in-picture in the bottom-right corner."""
    H, W = canvas.shape[:2]
    pw = max(1, int(W * scale))
    ph = max(1, int(pw * cam_bgr.shape[0] / cam_bgr.shape[1]))
    cam = cv2.resize(cam_bgr, (pw, ph))
    x2, y2 = W - margin, H - margin
    x1, y1 = x2 - pw, y2 - ph
    canvas[y1:y2, x1:x2] = cam
    cv2.rectangle(canvas, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), border, 2)
    if label:
        cv2.putText(canvas, label, (x1 + 6, y1 + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, border, 2, cv2.LINE_AA)
    return canvas


def draw_banner(canvas, title: str, subtitle: str = "", height: int = 92):
    """Semi-transparent top banner with a title and optional subtitle."""
    W = canvas.shape[1]
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (W, height), (35, 28, 24), -1)
    cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)
    cv2.putText(canvas, title, (24, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    if subtitle:
        cv2.putText(canvas, subtitle, (24, 74),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (170, 200, 255), 2, cv2.LINE_AA)


def draw_score(canvas, score: int, label: str = "Served"):
    W = canvas.shape[1]
    cv2.putText(canvas, f"{label}: {score}", (W - 220, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 220, 255), 2, cv2.LINE_AA)


def flash(canvas, alpha: float, color=(60, 200, 60)):
    """Blend a full-frame color flash over the canvas (alpha 0..1)."""
    alpha = float(np.clip(alpha, 0.0, 1.0))
    if alpha <= 0:
        return
    overlay = np.empty_like(canvas)
    overlay[:] = color
    cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)
