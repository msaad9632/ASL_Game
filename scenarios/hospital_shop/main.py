"""Hospital scenario entry point.

Thin game loop: read webcam -> core.capture -> fill the rolling buffer -> verify the active sign
-> render the hospital scene. The learner works through a queue of "patients", each needing one
sign. Success fires ONLY on an overall verifier pass (every required parameter cleared) — never on
a single frame, never on handshape alone. On success the next patient steps up.

Reuses core/ and signs/ unchanged; only the theme/assets differ from the coffee-shop scenario.

Run:
    python -m scenarios.hospital_shop.main            # play
    python -m scenarios.hospital_shop.main --debug    # show live per-parameter scores
Keys: q = quit,  n = skip to the next patient (handy for practising one sign).
"""
from __future__ import annotations

import argparse
import time
from collections import deque

import cv2

from core.capture import Capture
from core.landmarks import HandStabilizer, RollingBuffer
from core.verifier import movement_debug, verify
from scenarios.hospital_shop.scene import HospitalScene
from signs import HELP, PAIN, MEDICINE, EMERGENCY

SUCCESS_SECONDS = 2.0
# Flicker-tolerant debounce: success fires when the sign verifies as passed on at least
# PASS_MIN_FRAMES frames within the last PASS_WINDOW seconds. This blocks single-frame flukes AND
# survives the brief handshape dropouts that happen mid-motion, without letting non-performance
# through (an idle/incidental hand never clears the movement gate, so it scores zero passing frames).
PASS_WINDOW = 0.6
PASS_MIN_FRAMES = 4

# The patient queue: (sign, banner title, how-to instruction). Cycles forever.
PATIENTS = [
    (HELP, "A patient needs HELP", "Rest your FIST on your open palm, then lift the fist straight UP"),
    (PAIN, "Where's the PAIN?", "Point both index fingers and move them TOWARD each other"),
    (MEDICINE, "Give the MEDICINE", "Twist your fingertips on your open palm, back and forth"),
    (EMERGENCY, "It's an EMERGENCY!", "Make a claw and SHAKE it quickly, side to side"),
]


def main(camera_index: int = 0, debug: bool = False) -> None:
    scene = HospitalScene()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise SystemExit(f"Could not open webcam (index {camera_index}). Try --camera 1.")

    idx = 0
    buffer = RollingBuffer(window_seconds=1.5)       # short window: stale motion evicts quickly
    stabilizer = HandStabilizer(hold_seconds=0.3)    # bridge brief hand-detection dropouts
    score = 0
    state = "playing"          # "playing" | "success"
    success_start = 0.0
    pass_window = deque()      # recent (timestamp, passed?) within PASS_WINDOW, for the debounce
    t0 = time.monotonic()
    last_log = 0.0             # throttled debug transcript so results can be reviewed

    win = "ASL Hospital"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, scene.W, scene.H)

    def advance():
        nonlocal idx, state
        idx = (idx + 1) % len(PATIENTS)
        state = "playing"
        pass_window.clear()
        buffer.clear()

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

            sign, title, instruction = PATIENTS[idx]
            result = verify(buffer, sign)
            now = time.monotonic()

            if debug and frame.hands and (t - last_log) > 0.5:
                bits = "  ".join(f"{p.name.split('_')[0][:4]}:{p.score:.2f}" for p in result.params)
                print(f"[{t:6.1f}s] {sign.name:9s} {'PASS' if result.passed else 'fail':4s}  {bits}", flush=True)
                last_log = t

            # Flicker-tolerant debounce: fire only when the sign verified as passed on enough frames
            # within the recent window. A single fluke (or a frozen/idle hand that never clears the
            # movement gate) can't reach the count; a real sign whose handshape briefly drops out
            # mid-motion still does.
            if state == "playing":
                pass_window.append((now, result.passed))
                while pass_window and now - pass_window[0][0] > PASS_WINDOW:
                    pass_window.popleft()
                if sum(1 for _, p in pass_window if p) >= PASS_MIN_FRAMES:
                    state = "success"
                    success_start = now
                    score += 1
                    print(f"[{t:6.1f}s] *** {sign.name} TREATED (score={score}) ***", flush=True)
                    buffer.clear()          # avoid immediately re-triggering on the same motion
                    pass_window.clear()

            progress = 0.0
            if state == "success":
                progress = (now - success_start) / SUCCESS_SECONDS
                if progress >= 1.0:
                    advance()
                    continue

            debug_overlay = (result, movement_debug(buffer, sign)) if debug else None
            canvas = scene.render(bgr, title, instruction, score, state, progress, debug_overlay)
            cv2.imshow(win, canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("n"):
                advance()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0, help="webcam index")
    ap.add_argument("--debug", action="store_true", help="show live per-parameter scores")
    args = ap.parse_args()
    main(args.camera, args.debug)
