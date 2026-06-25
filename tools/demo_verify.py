"""Phase 3 live harness: run the generic verifier against a chosen hospital sign.

Opens the webcam, fills the rolling buffer, and every frame runs `core.verifier.verify(buffer,
active_sign)`, drawing the per-parameter scores (handshape / location / movement / orientation)
with each one colored green if it clears its threshold and red if it doesn't, plus the overall
PASS/FAIL. This is the tool to *see why* a sign passes or fails — especially that a frozen pose
keeps the movement score red.

Switch the active sign with number keys; quit with 'q'.
    1 HELP   2 PAIN   3 MEDICINE   4 EMERGENCY   5 A (static control)

Run (venv active, models downloaded):
    python -m tools.demo_verify
"""
from __future__ import annotations

import time

import cv2

from core.capture import Capture
from core.landmarks import RollingBuffer
from core.verifier import verify
from signs import HELP, PAIN, MEDICINE, EMERGENCY, LETTER_A

SIGN_KEYS = {
    ord("1"): HELP,
    ord("2"): PAIN,
    ord("3"): MEDICINE,
    ord("4"): EMERGENCY,
    ord("5"): LETTER_A,
}

GREEN = (0, 200, 0)
RED = (0, 0, 255)
WHITE = (255, 255, 255)
GREY = (160, 160, 160)


def _draw_panel(bgr, sign, result, buffer):
    h, w = bgr.shape[:2]
    x0, y0 = 10, 10
    cv2.rectangle(bgr, (x0, y0), (x0 + 360, y0 + 200), (30, 30, 30), -1)
    cv2.putText(bgr, f"SIGN: {sign.name}", (x0 + 12, y0 + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2, cv2.LINE_AA)

    y = y0 + 64
    for param in ("handshape", "location", "movement", "orientation"):
        s = result.scores[param]
        thr = result.thresholds[param]
        is_required = param in result.required
        if not is_required:
            color = GREY
            tag = "(not gated)"
        else:
            color = GREEN if s >= thr else RED
            tag = f">= {thr:.2f}"
        cv2.putText(bgr, f"{param:12s} {s:.2f}  {tag}", (x0 + 12, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
        y += 28

    verdict = "PASS" if result.passed else "FAIL"
    vcolor = GREEN if result.passed else RED
    cv2.putText(bgr, verdict, (x0 + 12, y + 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, vcolor, 2, cv2.LINE_AA)
    if not result.passed and result.failed:
        cv2.putText(bgr, f"failing: {', '.join(result.failed)}", (x0 + 110, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 1, cv2.LINE_AA)

    hint = "keys: 1 HELP  2 PAIN  3 MEDICINE  4 EMERGENCY  5 A   q quit"
    cv2.putText(bgr, hint, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1, cv2.LINE_AA)
    cv2.putText(bgr, f"buffer {len(buffer)}f / {buffer.duration:.1f}s",
                (w - 230, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)


def main(camera_index: int = 0, window_seconds: float = 1.8) -> None:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam (index {camera_index}).")

    buffer = RollingBuffer(window_seconds=window_seconds)
    active = HELP
    t0 = time.monotonic()
    last_log = 0.0
    was_passing = False
    print(f"[demo] active sign: {active.name}  (gated params: {active.required_parameters()})", flush=True)

    with Capture() as capture:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            bgr = cv2.flip(bgr, 1)  # mirror so motion feels natural
            t = time.monotonic() - t0
            frame = capture.process(bgr, timestamp_ms=int(t * 1000), t_seconds=t)
            buffer.add(frame)

            # landmarks (green) + palm centers (red)
            for hand in frame.hands:
                for x, y, _z in hand.points:
                    cv2.circle(bgr, (int(x), int(y)), 2, GREEN, -1)
                cx, cy = hand.center
                cv2.circle(bgr, (int(cx), int(cy)), 6, RED, -1)

            result = verify(buffer, active)
            _draw_panel(bgr, active, result, buffer)

            # --- throttled stdout transcript so scores can be reviewed after quitting ---
            if frame.hands and (t - last_log) > 0.5:
                print(f"[{t:6.1f}s] {active.name:9s} {result}", flush=True)
                last_log = t
            if result.passed and not was_passing:
                print(f"[{t:6.1f}s] *** {active.name} PASSED *** {result.scores}", flush=True)
            was_passing = result.passed

            cv2.imshow("ASL_Game - Phase 3 verifier (hospital)", bgr)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key in SIGN_KEYS:
                active = SIGN_KEYS[key]
                buffer.clear()  # fresh window when switching signs
                was_passing = False
                print(f"[demo] active sign: {active.name}  (gated params: {active.required_parameters()})", flush=True)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
