"""Hospital scenario presentation/theme.

Draws the gamified screen: a hospital background (assets/background.png if present, else a
procedural clinic), the patient-request banner, a picture-in-picture webcam, the score HUD, and a
success animation (green flash + a medical cross that fills). Recognition is NOT here — this
module only renders. It consumes a VerifyResult; it never decides pass/fail itself.

Mirrors scenarios/coffee_shop/scene.py and reuses the shared mechanics in core/game.py so the two
scenarios feel consistent under different themes.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core import game

ASSETS = Path(__file__).parent / "assets"

# theme palette (BGR)
WALL_TOP = (210, 200, 188)
WALL_BOT = (180, 170, 156)
DESK = (150, 120, 92)
CROSS_RED = (60, 60, 220)
CROSS_GREEN = (70, 200, 90)


class HospitalScene:
    def __init__(self, width: int = 1280, height: int = 720):
        self.W = width
        self.H = height
        self.bg = self._load_or_make_background()

    # ----------------------------------------------------------------- background
    def _load_or_make_background(self):
        path = ASSETS / "background.png"
        if path.exists():
            img = cv2.imread(str(path))
            if img is not None:
                return cv2.resize(img, (self.W, self.H))
        return self._procedural_background()

    def _procedural_background(self):
        W, H = self.W, self.H
        bg = np.zeros((H, W, 3), np.uint8)
        # clean clinic wall: vertical gradient
        for y in range(H):
            f = y / H
            bg[y, :] = [int(WALL_TOP[c] + (WALL_BOT[c] - WALL_TOP[c]) * f) for c in range(3)]
        # floor band + reception desk along the bottom
        cv2.rectangle(bg, (0, int(H * 0.74)), (W, H), (165, 145, 120), -1)
        cv2.rectangle(bg, (0, int(H * 0.74)), (W, int(H * 0.74) + 12), (120, 95, 70), -1)
        cv2.rectangle(bg, (int(W * 0.05), int(H * 0.60)), (int(W * 0.50), int(H * 0.80)), DESK, -1)
        cv2.putText(bg, "RECEPTION", (int(W * 0.10), int(H * 0.71)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (235, 235, 235), 2, cv2.LINE_AA)

        # wall cross sign (white plate + red cross) + hospital name, sitting below the top banner
        self._draw_cross(bg, cx=72, cy=158, size=64, fill=0.0, frame=True)
        cv2.putText(bg, "CITY GENERAL HOSPITAL", (130, 168),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (60, 60, 60), 2, cv2.LINE_AA)

        # triage board (top-right) listing the signs the learner will practice
        x1, y1, x2, y2 = int(W * 0.62), int(H * 0.16), int(W * 0.94), int(H * 0.56)
        cv2.rectangle(bg, (x1, y1), (x2, y2), (245, 245, 245), -1)
        cv2.rectangle(bg, (x1, y1), (x2, y2), (120, 95, 70), 4)
        cv2.putText(bg, "TRIAGE BOARD", (x1 + 22, y1 + 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (60, 60, 60), 2, cv2.LINE_AA)
        for i, item in enumerate(("HELP", "PAIN", "MEDICINE", "EMERGENCY")):
            cv2.putText(bg, f"- {item}", (x1 + 26, y1 + 92 + i * 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (70, 70, 70), 2, cv2.LINE_AA)
        return bg

    # ----------------------------------------------------------------- medical cross icon
    def _draw_cross(self, img, cx, cy, size, fill: float, frame: bool = False):
        """A medical cross centered at (cx, cy). `fill` (0..1) tints it green from the bottom up."""
        arm = size // 3
        if frame:
            cv2.rectangle(img, (cx - size // 2 - 8, cy - size // 2 - 8),
                          (cx + size // 2 + 8, cy + size // 2 + 8), (245, 245, 245), -1)
        # the two bars of the cross (red by default)
        vbar = (cx - arm // 2, cy - size // 2, cx + arm // 2, cy + size // 2)
        hbar = (cx - size // 2, cy - arm // 2, cx + size // 2, cy + arm // 2)
        for (bx1, by1, bx2, by2) in (vbar, hbar):
            cv2.rectangle(img, (bx1, by1), (bx2, by2), CROSS_RED, -1)
        # green fill rising from the bottom as treatment completes
        fill = float(np.clip(fill, 0.0, 1.0))
        if fill > 0:
            fy = int(cy + size // 2 - size * fill)
            sub = img[max(0, fy):cy + size // 2, cx - size // 2:cx + size // 2 + 1]
            if sub.size:
                mask = np.all(sub == np.array(CROSS_RED), axis=-1)
                sub[mask] = CROSS_GREEN

    # ----------------------------------------------------------------- render
    def render(self, cam_bgr, title: str, instruction: str, score: int, state: str,
               success_progress: float = 0.0, debug_overlay=None):
        canvas = self.bg.copy()
        game.draw_banner(canvas, title, instruction)
        game.draw_score(canvas, score, label="Treated")

        # the "current patient" cross near the desk fills green while a success plays
        cross_fill = success_progress if state == "success" else 0.0
        self._draw_cross(canvas, cx=int(self.W * 0.40), cy=int(self.H * 0.46),
                         size=120, fill=cross_fill, frame=True)

        game.composite_pip(canvas, cam_bgr)

        if state == "success":
            game.flash(canvas, 0.45 * (1.0 - success_progress), CROSS_GREEN)
            text = "PATIENT HELPED!"
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
            cv2.putText(canvas, text, ((self.W - tw) // 2, self.H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)

        if debug_overlay is not None:
            result, move_dbg = debug_overlay
            from core.overlay import draw_param_scores
            draw_param_scores(canvas, result, move_dbg, y0=112)   # below the top banner

        return canvas
