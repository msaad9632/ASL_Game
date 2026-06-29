"""Guided batch recorder: capture a real sample of every hospital sign in one session.

For each sign it opens the preview (showing the sign + how to perform it); press SPACE to start,
do the sign for ~4s, and it advances to the next. Each clip is saved to tests/fixtures/<name>_real
.json — real landmark data used to calibrate the sign definitions to how YOU actually sign (and as
our own dataset). Press 'q' on any preview to skip that sign.

    python -m tools.record_all
"""
from __future__ import annotations

from core.recorder import record

# (fixture base, SIGN, how-to shown on the preview)
PLAN = [
    ("help", "HELP", "fist on open palm, lift BOTH up"),
    ("pain", "PAIN", "two index fingers, move TOGETHER"),
    ("medicine", "MEDICINE", "claw twisting over your open palm"),
    ("emergency", "EMERGENCY", "claw hand, SHAKE it fast"),
    ("doctor", "DOCTOR", "flat hand: TAP the opposite wrist x2"),
    ("nurse", "NURSE", "two fingers (N): TAP the opposite wrist x2"),
    ("sick", "SICK", "middle fingers: one at forehead, one at belly"),
    ("fever", "FEVER", "open hand: SWEEP across your forehead"),
    ("water", "WATER", "three fingers (W): TAP your chin x2"),
    ("breathe", "BREATHE", "open hands on chest: move OUT then IN"),
    ("hospital", "HOSPITAL", "two fingers (H) at opposite shoulder: draw a cross"),
    ("dizzy", "DIZZY", "claw at your face: CIRCLE it"),
]


def main(seconds: float = 4.0) -> None:
    done = []
    for base, sign, how in PLAN:
        print(f"\n=== {sign} — {how} ===  (SPACE to record, q to skip)")
        frames = record(f"tests/fixtures/{base}_real.json", seconds=seconds, sign_name=f"{sign}: {how}")
        done.append((base, len(frames)))
    print("\nRecorded:")
    for base, n in done:
        print(f"  {base}_real.json: {n} frames")


if __name__ == "__main__":
    main()
