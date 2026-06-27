"""Coffee-shop presentation/theme.

Draws the gamified screen: a coffee-shop background (assets/background.png if present, else a
procedural cafe), the order-prompt banner, a picture-in-picture webcam, the score HUD, and a
success animation (green flash + a coffee cup that fills). Recognition is NOT here — this module
only renders. It consumes a VerifyResult; it never decides pass/fail itself.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core import game

ASSETS = Path(__file__).parent / "assets"


class CoffeeShopScene:
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
        # warm wall, vertical gradient (BGR)
        for y in range(H):
            f = y / H
            bg[y, :] = (int(70 + 25 * f), int(95 + 35 * f), int(120 + 45 * f))
        # counter along the bottom
        cv2.rectangle(bg, (0, int(H * 0.72)), (W, H), (45, 60, 90), -1)
        cv2.rectangle(bg, (0, int(H * 0.72)), (W, int(H * 0.72) + 12), (28, 38, 60), -1)
        # chalkboard menu (top-right)
        x1, y1, x2, y2 = int(W * 0.60), int(H * 0.14), int(W * 0.93), int(H * 0.55)
        cv2.rectangle(bg, (x1, y1), (x2, y2), (32, 32, 32), -1)
        cv2.rectangle(bg, (x1, y1), (x2, y2), (70, 85, 110), 6)
        cv2.putText(bg, "MENU", (x1 + 26, y1 + 46),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (235, 235, 235), 2, cv2.LINE_AA)
        for i, item in enumerate(("Coffee", "Latte", "Espresso", "Mocha")):
            cv2.putText(bg, f"- {item}", (x1 + 26, y1 + 90 + i * 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 210, 210), 1, cv2.LINE_AA)
        # cafe name + a cup icon
        cv2.putText(bg, "THE CODE CAFE", (40, int(H * 0.46)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (245, 245, 245), 3, cv2.LINE_AA)
        self._draw_cup(bg, cx=120, cy=int(H * 0.60), w=120, h=120, fill=0.0)
        return bg

    # ----------------------------------------------------------------- coffee cup
    def _draw_cup(self, img, cx, cy, w, h, fill: float):
        """A simple mug outline filled `fill` (0..1) with coffee."""
        x1, y1, x2, y2 = cx, cy, cx + w, cy + h
        # coffee fill (from the bottom up)
        fill = float(np.clip(fill, 0.0, 1.0))
        if fill > 0:
            fy = int(y2 - (y2 - y1 - 8) * fill)
            cv2.rectangle(img, (x1 + 6, fy), (x2 - 6, y2 - 6), (35, 70, 110), -1)
        # mug body + handle
        cv2.rectangle(img, (x1, y1), (x2, y2), (230, 230, 230), 3)
        cv2.ellipse(img, (x2 + 14, (y1 + y2) // 2), (16, 26), 0, -90, 90, (230, 230, 230), 3)

    # ----------------------------------------------------------------- render
    def render(self, cam_bgr, prompt_text: str, score: int, state: str,
               success_progress: float = 0.0, debug_overlay=None):
        canvas = self.bg.copy()
        game.draw_banner(canvas, "Customer order:", prompt_text)
        game.draw_score(canvas, score)

        # the "current order" cup near the counter fills while a success plays
        cup_fill = success_progress if state == "success" else 0.0
        self._draw_cup(canvas, cx=int(self.W * 0.40), cy=int(self.H * 0.50),
                       w=110, h=110, fill=cup_fill)

        game.composite_pip(canvas, cam_bgr)

        if state == "success":
            game.flash(canvas, 0.45 * (1.0 - success_progress), (60, 200, 60))
            text = "COFFEE SERVED!"
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
            cv2.putText(canvas, text, ((self.W - tw) // 2, self.H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)

        if debug_overlay is not None:
            result, move_dbg = debug_overlay
            from core.overlay import draw_param_scores
            draw_param_scores(canvas, result, move_dbg, y0=112)   # below the top banner

        return canvas
