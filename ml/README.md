# ML Recognition Pipeline (Phase C)

Trains an ASL Citizen word-classifier that runs **alongside** the rule verifier as a
**disambiguation layer** — it does not replace the per-parameter Sign Coach. See the Phase C
plan for the full rationale.

## Data flow (one extraction, many consumers)

```
video files ──▶ tools/extract_dataset.py ──▶ data/landmarks/<SIGN>/*.json   (Frame JSON)
                       │ 1€ filter, signer-split manifest
                       ▼
                data/manifest.csv
                       │
   ml/dataset.py ──▶ data/cache.npz   (X:(N,48,86)  y  split  classes)
                       │
   ml/inspect.py ──▶ ml/inspect_out/*.png   ◀── GATE: eyeball before training
                       │
   ml/train.py ───▶ ml/runs/model_vN/   (model.keras, tfjs/, confusion_matrix.png,
                       │                  metrics.json incl. minimal-pair report)
                       ▼
   web/src/engine/classifier.ts (C.5)   ◀── TF.js model, gated next to verify()
```

The `Frame` JSON is the **same format** the rule verifier, the confusor tests, the avatar
pipeline, and this trainer all read. Don't invent a second format.

## Local smoke test (no GPU, proves the code path)

```bash
# 1. extract landmarks from any folder where filename = sign
python -m tools.extract_dataset footage --src "D:/asl-synthesis/footage" --out data/landmarks
python -m tools.verify_extracted data/landmarks        # confirm rule engine reads it

# 2. build the cache
python -m ml.dataset --landmarks data/landmarks --manifest data/manifest.csv

# 3. GATE: render + health-check before training
python -m ml.inspect            # open ml/inspect_out/*.png, confirm each sign reads right

# 4. verify the training data path (no TensorFlow needed)
python -m ml.train --dry-run
```

## Real run on Kaggle (ASL Citizen)

1. Add the ASL Citizen dataset to a Kaggle notebook (Add Data).
2. Extract landmarks (resumable, multi-session if needed):
   ```bash
   python -m tools.extract_dataset dataset \
     --videos /kaggle/input/asl-citizen/videos \
     --labels /kaggle/input/asl-citizen/labels.csv \
     --col-file video_file --col-gloss gloss --col-signer participant_id \
     --out /kaggle/working/data/landmarks
   ```
   Extraction (CPU MediaPipe over 84k clips) is the real bottleneck — not GPU training.
3. `python -m ml.dataset --landmarks /kaggle/working/data/landmarks --manifest /kaggle/working/data/manifest.csv`
4. `python -m ml.inspect` — **do not skip the gate**.
5. `pip install tensorflowjs && python -m ml.train --epochs 60`
6. Download `ml/runs/model_vN/tfjs/` and wire it into the web app (C.5).

## Staging (decided in planning)

Smoke-test on the ~24 **game** signs first (fast, proves the pipeline), then scale to full
ASL Citizen with identical code. The full model's logits are mapped down to the game
vocabulary for the in-browser disambiguation gate.

## Notes
- **Split by signer, not by video** — `extract_dataset.py dataset` does this in the manifest.
- **Augmentation** (`ml/augment.py`): rotation / scale / time-warp / jitter only. Horizontal
  mirroring is intentionally excluded (it corrupts handedness + orientation labels).
- Bulk outputs (`data/`, `ml/runs/`, `ml/inspect_out/`) are gitignored — regenerable.
