"""MediaPipe Tasks (Hand + Pose) capture wrapper -> normalized Frame.

Wraps HandLandmarker + PoseLandmarker (the Tasks API, VIDEO running mode) into a single
`process()` call that returns a core.landmarks.Frame in pixel coordinates. The Tasks API is
used deliberately so this logic ports cleanly to @mediapipe/tasks-vision in the browser later.

Model files are not committed; download them into models/ (see models/README.md).
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np

try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import vision as mp_vision
except ImportError as exc:  # pragma: no cover - guidance, not logic
    raise ImportError(
        "Phase 1 needs mediapipe + opencv-python.\n"
        "Activate the venv and run:  pip install -r requirements.txt"
    ) from exc

from core.landmarks import Frame, Hand, POSE_LEFT_SHOULDER, POSE_RIGHT_SHOULDER

DEFAULT_HAND_MODEL = os.path.join("models", "hand_landmarker.task")
DEFAULT_POSE_MODEL = os.path.join("models", "pose_landmarker_lite.task")


class Capture:
    """Runs hand + pose landmarking on successive webcam frames.

    Use one instance for the lifetime of a capture session (the Tasks VIDEO mode tracks state
    across frames). Call process() per frame with a strictly increasing timestamp.
    """

    def __init__(
        self,
        hand_model: str = DEFAULT_HAND_MODEL,
        pose_model: str = DEFAULT_POSE_MODEL,
        num_hands: int = 2,
    ):
        for path, what in ((hand_model, "hand"), (pose_model, "pose")):
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Missing MediaPipe {what} model: {path}\n"
                    f"Download it into models/ — see models/README.md."
                )

        base = mp.tasks.BaseOptions
        running_mode = mp_vision.RunningMode.VIDEO

        self._hand = mp_vision.HandLandmarker.create_from_options(
            mp_vision.HandLandmarkerOptions(
                base_options=base(model_asset_path=hand_model),
                running_mode=running_mode,
                num_hands=num_hands,
                # Closed fists are harder to detect than open hands; lower thresholds so the two
                # stacked fists in COFFEE are picked up across more frames.
                min_hand_detection_confidence=0.4,
                min_hand_presence_confidence=0.4,
                min_tracking_confidence=0.4,
            )
        )
        self._pose = mp_vision.PoseLandmarker.create_from_options(
            mp_vision.PoseLandmarkerOptions(
                base_options=base(model_asset_path=pose_model),
                running_mode=running_mode,
                num_poses=1,
            )
        )
        self._last_ts_ms = -1

    def process(self, bgr_image: np.ndarray, timestamp_ms: int, t_seconds: Optional[float] = None) -> Frame:
        """Detect hands + pose in one BGR frame and return a normalized Frame.

        `timestamp_ms` must be non-decreasing across calls (VIDEO mode requirement); we bump it
        forward if a caller repeats one. `t_seconds` is the wall-clock-ish time stored on the
        Frame (defaults to timestamp_ms / 1000).
        """
        if timestamp_ms <= self._last_ts_ms:
            timestamp_ms = self._last_ts_ms + 1
        self._last_ts_ms = timestamp_ms

        h, w = bgr_image.shape[:2]
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        hand_res = self._hand.detect_for_video(mp_image, timestamp_ms)
        pose_res = self._pose.detect_for_video(mp_image, timestamp_ms)

        frame = Frame(
            t=timestamp_ms / 1000.0 if t_seconds is None else t_seconds,
            width=w,
            height=h,
        )

        if hand_res.hand_landmarks:
            for lms, handedness in zip(hand_res.hand_landmarks, hand_res.handedness):
                label = handedness[0].category_name  # "Left" / "Right"
                pts = np.array([[lm.x * w, lm.y * h, lm.z] for lm in lms], dtype=float)
                frame.hands.append(Hand(handedness=label, points=pts))

        if pose_res.pose_landmarks:
            pose = pose_res.pose_landmarks[0]
            ls, rs = pose[POSE_LEFT_SHOULDER], pose[POSE_RIGHT_SHOULDER]
            frame.left_shoulder = np.array([ls.x * w, ls.y * h], dtype=float)
            frame.right_shoulder = np.array([rs.x * w, rs.y * h], dtype=float)

        return frame

    def close(self) -> None:
        self._hand.close()
        self._pose.close()

    def __enter__(self) -> "Capture":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
