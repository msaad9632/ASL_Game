"""Phase 3 live demo: per-parameter verifier scores for a chosen sign.

This is the Phase 5 debug overlay brought forward so you can SEE the verifier judging your sign
in real time. It draws hand landmarks + a scorecard: one bar per parameter (green once it clears
its threshold, red below), which hand is dominant, and the overall PASS state.

Run (venv active, models downloaded):
    python -m tools.demo_verify                 # COFFEE by default
    python -m tools.demo_verify --sign LETTER_A
Press 'q' to quit.
"""
from __future__ import annotations

import argparse
import time

import cv2
import numpy as np

from core.capture import Capture
from core.landmarks import RollingBuffer
from core.verifier import movement_debug, verify
from signs import SIGNS


def _draw_scorecard(img, result, move_dbg: str) -> None:
    x, y, line = 12, 34, 30
    banner = "PASS" if result.passed else "sign it..."
    color = (0, 200, 0) if result.passed else (0, 165, 255)
    cv2.putText(img, f"{result.sign_name}:  {banner}", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)
    dom = result.roles.get("dominant", "-")
    cv2.putText(img, f"dominant hand: {dom}", (x, y + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
    y += 52
    for p in result.params:
        if p.cleared:
            col = (0, 200, 0)                       # green: cleared its threshold
        elif p.required:
            col = (0, 0, 255)                       # red: required and below threshold
        else:
            col = (130, 130, 130)                   # gray: optional, doesn't block
        bar = int(np.clip(p.score, 0.0, 1.0) * 130)
        cv2.rectangle(img, (x, y - 13), (x + 130, y + 1), (70, 70, 70), 1)
        cv2.rectangle(img, (x, y - 13), (x + bar, y + 1), col, -1)
        tag = "req" if p.required else "opt-ignored"
        txt_col = (255, 255, 255) if p.required else (150, 150, 150)
        cv2.putText(img, f"{p.name:<22}{p.score:0.2f} / {p.threshold:0.2f} [{tag}]",
                    (x + 140, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, txt_col, 1, cv2.LINE_AA)
        y += line
    # live movement sub-metrics (the calibration readout)
    cv2.putText(img, f"movement: {move_dbg}", (x, y + 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)


def main(sign_name: str = "COFFEE", camera_index: int = 0) -> None:
    if sign_name not in SIGNS:
        raise SystemExit(f"Unknown sign '{sign_name}'. Known: {list(SIGNS)}")
    sign = SIGNS[sign_name]

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise SystemExit(f"Could not open webcam (index {camera_index}). Try --camera 1.")

    buffer = RollingBuffer(window_seconds=2.0)
    t0 = time.monotonic()
    print(f"[demo_verify] running for sign {sign_name}; press 'q' in the window to quit.")

    win = f"ASL_Game Phase 3 - verify {sign_name} (q to quit)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    with Capture() as capture:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            bgr = cv2.flip(bgr, 1)
            t = time.monotonic() - t0
            frame = capture.process(bgr, timestamp_ms=int(t * 1000), t_seconds=t)
            buffer.add(frame)

            for hand in frame.hands:
                for px, py, _z in hand.points:
                    cv2.circle(bgr, (int(px), int(py)), 3, (0, 255, 0), -1)
                cx, cy = hand.center
                cv2.circle(bgr, (int(cx), int(cy)), 6, (0, 0, 255), -1)
            if frame.left_shoulder is not None and frame.right_shoulder is not None:
                for sx, sy in (frame.left_shoulder, frame.right_shoulder):
                    cv2.circle(bgr, (int(sx), int(sy)), 6, (255, 0, 0), -1)

            _draw_scorecard(bgr, verify(buffer, sign), movement_debug(buffer, sign))
            cv2.imshow(win, bgr)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sign", default="COFFEE", help="sign name from the registry (COFFEE, LETTER_A)")
    ap.add_argument("--camera", type=int, default=0, help="webcam index")
    args = ap.parse_args()
    main(args.sign, args.camera)
