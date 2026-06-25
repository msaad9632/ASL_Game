# MediaPipe model files

The recognition engine uses the MediaPipe **Tasks API**, which loads `.task` model bundles.
These files are **not committed** (they're binary weights, git-ignored via `*.task`). Each
developer downloads them once into this folder.

## Required files

| File                        | Purpose                  | Download |
|-----------------------------|--------------------------|----------|
| `hand_landmarker.task`      | 21 landmarks per hand    | https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models |
| `pose_landmarker_lite.task` | body pose (shoulders for normalization) | https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models |

The `_lite` pose model is enough — we only need the shoulder points for scale normalization.

After downloading, this folder should contain:

```
models/
├── README.md            (committed)
├── hand_landmarker.task (git-ignored)
└── pose_landmarker_lite.task (git-ignored)
```

> Exact download commands are added to the root README in Phase 1, when capture.py starts
> loading these files.
