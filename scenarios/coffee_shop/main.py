"""Coffee-shop scenario entry point.

A multi-sign game loop: the customer asks for a series of signs (COFFEE -> PLEASE -> THANK YOU),
the player performs each, earns POINTS_PER_SIGN for a correct one, and the game advances to the
next prompt and loops forever. Success fires ONLY on an overall verifier pass (every required
parameter cleared) — never a single frame.

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
from signs import COFFEE, PLEASE, THANK_YOU

SUCCESS_SECONDS = 1.6
POINTS_PER_SIGN = 10

# the order the customer asks for; loops forever
PROMPTS = [
    (COFFEE, "Order a COFFEE - grind your fists, one over the other"),
    (PLEASE, "Say PLEASE - open hand circling on your chest"),
    (THANK_YOU, "Say THANK YOU - open hand from your chin, moving down"),
]


def main(camera_index: int = 0, debug: bool = False) -> None:
    scene = CoffeeShopScene()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise SystemExit(f"Could not open webcam (index {camera_index}). Try --camera 1.")

    buffer = RollingBuffer(window_seconds=2.0)
    stabilizer = HandStabilizer(hold_seconds=0.3)
    score = 0
    idx = 0                       # which prompt we're on
    state = "playing"            # "playing" | "success"
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
            frame = stabilizer.stabilize(frame)
            buffer.add(frame)

            sign, prompt = PROMPTS[idx]
            result = verify(buffer, sign)
            now = time.monotonic()

            if state == "playing" and result.passed:
                state = "success"
                success_start = now
                score += POINTS_PER_SIGN
                buffer.clear()
                stabilizer.reset()

            progress = 0.0
            if state == "success":
                progress = (now - success_start) / SUCCESS_SECONDS
                if progress >= 1.0:
                    state = "playing"
                    idx = (idx + 1) % len(PROMPTS)     # advance to the next sign, loop forever

            canvas = scene.render(
                bgr, prompt, score, state, progress,
                debug_overlay=(result, movement_debug(buffer, sign)) if debug else None,
                success_text=f"CORRECT!  +{POINTS_PER_SIGN}",
            )
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
