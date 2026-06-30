"""C.2 — Dataset builder: Frame JSON -> cached training tensors (.npz).

JSON stays the source of truth; this converts ONCE into a compact numpy cache the trainer
reads repeatedly. Feature design mirrors the rule engine's invariances so the model learns
the sign, not the camera:

  * Per frame, each hand's 21 (x, y) landmarks are centered on the shoulder midpoint and
    scaled by shoulder width -> translation- and camera-distance-invariant (the same ratio
    trick `normalized_distance` uses in core/landmarks.py). MediaPipe z is dropped: it's a
    per-hand relative depth, not in shoulder-width units, and noisy.
  * Hands are slotted by handedness (Right -> slot 0, Left -> slot 1) so the channel order is
    stable across clips. A missing hand is zeros + a presence flag so the model can tell
    "hand at origin" from "hand absent".
  * Normalization constants (shoulder midpoint + width) are taken once per clip (median over
    frames with pose) so the normalization itself doesn't jitter, and missing-pose frames
    still get sane features. Fallback to hand-based scale if a clip never sees shoulders.
  * Time is linearly resampled to a fixed SEQ_LEN, normalizing different fps/durations.

Output: data/cache.npz with X (N, SEQ_LEN, F), y (N,), split (N,), and classes (C,).

    python -m ml.dataset --landmarks data/landmarks --manifest data/manifest.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Optional

import numpy as np

SEQ_LEN = 48
N_LANDMARKS = 21
PER_HAND = N_LANDMARKS * 2          # x, y only
PER_HAND_F = PER_HAND + 1           # + presence flag
FEAT_DIM = PER_HAND_F * 2           # two hands -> 86
HAND_SLOTS = ("Right", "Left")

# Hand landmark indices (mirror core/landmarks.py) for the fallback scale.
WRIST, MIDDLE_MCP = 0, 9


# ----------------------------------------------------------------- per-clip normalization

def _clip_norm(frames: list[dict]) -> tuple[np.ndarray, float]:
    """Return (mid_xy, scale) constants for a clip from median shoulder geometry."""
    mids, widths = [], []
    for fr in frames:
        ls, rs = fr.get("left_shoulder"), fr.get("right_shoulder")
        if ls is not None and rs is not None:
            ls, rs = np.asarray(ls, float), np.asarray(rs, float)
            w = float(np.linalg.norm(ls - rs))
            if w > 1e-6:
                mids.append((ls + rs) / 2.0)
                widths.append(w)
    if widths:
        return np.median(np.stack(mids), axis=0), float(np.median(widths))

    # Fallback: no pose anywhere. Center on median wrist, scale by median hand span.
    wrists, spans = [], []
    for fr in frames:
        for h in fr["hands"]:
            pts = np.asarray(h["points"], float)
            wrists.append(pts[WRIST, :2])
            spans.append(float(np.linalg.norm(pts[WRIST, :2] - pts[MIDDLE_MCP, :2])))
    if spans:
        # A hand span is ~0.3 shoulder-widths; scale up so magnitudes land in a similar range.
        return np.median(np.stack(wrists), axis=0), max(float(np.median(spans)) / 0.3, 1e-6)
    return np.zeros(2), 1.0


def _frame_features(fr: dict, mid: np.ndarray, scale: float) -> np.ndarray:
    """86-dim feature for one frame: [Right 42 + flag, Left 42 + flag]."""
    out = np.zeros(FEAT_DIM, dtype=np.float32)
    by_hand = {h["handedness"]: h for h in fr["hands"]}
    for slot, handed in enumerate(HAND_SLOTS):
        base = slot * PER_HAND_F
        h = by_hand.get(handed)
        if h is not None:
            pts = np.asarray(h["points"], float)[:, :2]
            norm = ((pts - mid) / scale).reshape(-1)
            out[base:base + PER_HAND] = norm
            out[base + PER_HAND] = 1.0
    return out


def clip_to_sequence(payload: dict, seq_len: int = SEQ_LEN) -> Optional[np.ndarray]:
    """Frame-JSON payload -> (seq_len, FEAT_DIM) array, or None if empty/no hands."""
    frames = payload.get("frames", [])
    if not frames or not any(fr["hands"] for fr in frames):
        return None
    mid, scale = _clip_norm(frames)
    feats = np.stack([_frame_features(fr, mid, scale) for fr in frames])  # (N, F)
    return _resample_time(feats, seq_len)


def _resample_time(feats: np.ndarray, seq_len: int) -> np.ndarray:
    """Linearly resample a (N, F) sequence to (seq_len, F)."""
    n = feats.shape[0]
    if n == seq_len:
        return feats.astype(np.float32)
    src = np.linspace(0.0, n - 1, num=seq_len)
    lo = np.floor(src).astype(int)
    hi = np.minimum(lo + 1, n - 1)
    frac = (src - lo)[:, None]
    return (feats[lo] * (1 - frac) + feats[hi] * frac).astype(np.float32)


# ----------------------------------------------------------------- build

def _read_manifest(path: Path) -> dict[str, str]:
    """clip_id -> split. Empty dict if no manifest (everything defaults to train)."""
    splits: dict[str, str] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                splits[r["clip_id"]] = r.get("split", "train")
    return splits


def build(landmarks_dir: str, manifest: str, out: str, seq_len: int = SEQ_LEN) -> None:
    root = Path(landmarks_dir)
    split_map = _read_manifest(Path(manifest))

    X, y, splits, raw_labels = [], [], [], []
    skipped = 0
    for jp in sorted(root.rglob("*.json")):
        payload = json.loads(jp.read_text(encoding="utf-8"))
        seq = clip_to_sequence(payload, seq_len)
        if seq is None:
            skipped += 1
            continue
        sign = payload["sign_name"]
        clip_id = f"{jp.parent.name}/{jp.stem}"
        X.append(seq)
        raw_labels.append(sign)
        splits.append(split_map.get(clip_id, "train"))

    if not X:
        print("no usable clips found — nothing to cache")
        return

    classes = sorted(set(raw_labels))
    cls_idx = {c: i for i, c in enumerate(classes)}
    y = np.array([cls_idx[s] for s in raw_labels], dtype=np.int64)
    X = np.stack(X).astype(np.float32)
    splits = np.array(splits)

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, X=X, y=y, split=splits, classes=np.array(classes))

    print(f"cache -> {out_path}")
    print(f"  X={X.shape}  y={y.shape}  classes={len(classes)}  skipped={skipped}")
    for split in ("train", "val", "test"):
        print(f"  {split}: {(splits == split).sum()} clips")


def main() -> None:
    p = argparse.ArgumentParser(description="Build training cache from Frame JSON landmarks.")
    p.add_argument("--landmarks", default="data/landmarks")
    p.add_argument("--manifest", default="data/manifest.csv")
    p.add_argument("--out", default="data/cache.npz")
    p.add_argument("--seq-len", type=int, default=SEQ_LEN)
    args = p.parse_args()
    build(args.landmarks, args.manifest, args.out, args.seq_len)


if __name__ == "__main__":
    main()
