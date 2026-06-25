"""MediaPipe Tasks (Hand + Pose) capture wrapper -> normalized Frame.

Implemented in Phase 1. Wraps HandLandmarker + PoseLandmarker (Tasks API) into a single step
that yields a normalized Frame per webcam frame. Tasks API is chosen so the logic ports to
@mediapipe/tasks-vision in the browser later. Model files live in models/ (see models/README.md).
"""
