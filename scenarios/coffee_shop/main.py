"""Coffee-shop scenario entry point.

Thin game loop: read webcam -> core.capture -> fill the rolling buffer -> verify the active
sign -> render the coffee-shop scene. The success state fires ONLY on an overall verifier pass
(every required parameter cleared) — never on a single frame, never on handshape alone.

Run:
    python -m scenarios.coffee_shop.main            # play
    python -m scenarios.coffee_shop.main --debug    # show live per-parameter scores
"""
from __future__ import annotations

import argparse
import time

import cv2

from core.capture import Capture
from core.landmarks import HandStabilizer, RollingBuffer
from core.verifier import movement_debug, verify
from scenarios.coffee_shop.scene import CoffeeShopScene
from signs import COFFEE

SUCCESS_SECONDS = 2.0
PROMPT = "Make a COFFEE - grind your top fist over the bottom one!"


def main(camera_index: int = 0, debug: bool = False) -> None:
    scene = CoffeeShopScene()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise SystemExit(f"Could not open webcam (index {camera_index}). Try --camera 1.")

    sign = COFFEE
    buffer = RollingBuffer(window_seconds=2.0)
    stabilizer = HandStabilizer(hold_seconds=0.3)   # bridge brief fist-detection dropouts
    score = 0
    state = "playing"          # "playing" | "success"
    success_start = 0.0
    t0 = time.monotonic()

    win = "ASL Coffee Shop"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, scene.W, scene.H)

    with Capture() as capture:
        while True:
            ok, bgr = cap.read()
            if not ok:
                continue
            bgr = cv2.flip(bgr, 1)
            t = time.monotonic() - t0
            frame = capture.process(bgr, timestamp_ms=int(t * 1000), t_seconds=t)
            frame = stabilizer.stabilize(frame)     # carry a recently-seen hand over brief gaps
            buffer.add(frame)

            result = verify(buffer, sign)
            now = time.monotonic()

            if state == "playing" and result.passed:
                state = "success"
                success_start = now
                score += 1
                buffer.clear()          # avoid immediately re-triggering on the same motion

            progress = 0.0
            if state == "success":
                progress = (now - success_start) / SUCCESS_SECONDS
                if progress >= 1.0:
                    state = "playing"

            debug_overlay = (result, movement_debug(buffer, sign)) if debug else None
            canvas = scene.render(bgr, PROMPT, score, state, progress, debug_overlay)
            cv2.imshow(win, canvas)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0, help="webcam index")
    ap.add_argument("--debug", action="store_true", help="show live per-parameter scores")
    args = ap.parse_args()
    main(args.camera, args.debug)
