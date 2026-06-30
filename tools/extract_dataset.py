"""C.1 — Batch landmark extractor: video files -> Frame JSON (the canonical fixture format).

Runs MediaPipe (core.capture.Capture, VIDEO mode) over video files and writes one
Frame-format JSON per clip, identical in shape to the hand-recorded fixtures in
web/tests/fixtures/ and tests/fixtures/. That single format is consumed by the verifier,
the confusor tests, the ML dataset builder, AND the avatar pipeline — one extraction, many
consumers.

The 1€ filter (tools/oneeuro.py) is applied per-handedness AFTER extraction and BEFORE
saving, so training data is smoothed-but-honest (occlusion gaps survive as missing hands).
NOTE: HandStabilizer is deliberately NOT used here — training data must stay raw.

Two input modes
---------------
1. Footage mode (testable today, no dataset needed):
     python -m tools.extract_dataset footage --src "D:/asl-synthesis/footage" --out data/landmarks
   Sign label = filename stem (e.g. HELLO.mp4 -> HELLO). Single signer ("self").

2. ASL Citizen mode (the real dataset):
     python -m tools.extract_dataset dataset --videos DIR --labels labels.csv \
        --col-file video_file --col-gloss gloss --col-signer participant_id --out data/landmarks
   Builds a manifest with a deterministic split BY SIGNER (never by video).

Both modes are resumable: an existing output JSON is skipped unless --force.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path
from typing import Optional

try:
    import cv2
except ImportError as exc:  # pragma: no cover
    raise ImportError("extract_dataset needs opencv-python (pip install -r requirements.txt)") from exc

# Allow running as a module from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.capture import Capture           # noqa: E402
from core.landmarks import Frame           # noqa: E402
from tools.oneeuro import OneEuroVector     # noqa: E402

HAND_DIM = 63  # 21 landmarks * 3 coords

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}


# ----------------------------------------------------------------------------- extraction

def extract_video(path: str, capture: Capture, sign_name: str,
                  apply_filter: bool = True) -> dict:
    """Run MediaPipe over one video and return a {sign_name, frames:[...]} dict."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise IOError(f"could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if fps <= 1e-3:
        fps = 30.0

    frames: list[Frame] = []
    idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        t = idx / fps
        frames.append(capture.process(bgr, timestamp_ms=int(t * 1000), t_seconds=t))
        idx += 1
    cap.release()

    if apply_filter:
        _smooth_hands_inplace(frames)

    return {"sign_name": sign_name, "frames": [f.to_dict() for f in frames]}


def _smooth_hands_inplace(frames: list[Frame]) -> None:
    """Apply a 1€ filter to each handedness track separately (gaps preserved)."""
    filters: dict[str, OneEuroVector] = {}
    last_t: dict[str, float] = {}
    for f in frames:
        for hand in f.hands:
            key = hand.handedness
            if key not in filters:
                filters[key] = OneEuroVector(HAND_DIM)
                last_t[key] = f.t
            dt = max(f.t - last_t[key], 0.0)
            flat = hand.points.reshape(-1).tolist()
            smoothed = filters[key](flat, dt)
            if smoothed is not None:
                hand.points = _reshape63(smoothed)
            last_t[key] = f.t


def _reshape63(flat: list[float]):
    import numpy as np
    return np.asarray(flat, dtype=float).reshape(21, 3)


def clip_stats(payload: dict) -> dict:
    """Quick health numbers for the manifest / inspector gate."""
    frames = payload["frames"]
    n = len(frames)
    with_any = sum(1 for fr in frames if fr["hands"])
    handed = {"Left": 0, "Right": 0}
    for fr in frames:
        for h in fr["hands"]:
            handed[h["handedness"]] = handed.get(h["handedness"], 0) + 1
    return {
        "n_frames": n,
        "hand_coverage": round(with_any / n, 3) if n else 0.0,
        "left_obs": handed.get("Left", 0),
        "right_obs": handed.get("Right", 0),
    }


# ----------------------------------------------------------------------------- modes

def run_footage(args, capture: Capture, writer: "ManifestWriter") -> None:
    src = Path(args.src)
    vids = sorted(p for p in src.iterdir() if p.suffix.lower() in VIDEO_EXTS)
    # Skip junk filenames that don't map to a known sign (e.g. "WhatsApp Video ...").
    vids = [p for p in vids if p.stem.replace("_", "").isalnum() and " " not in p.stem]
    print(f"[footage] {len(vids)} videos under {src}")
    for vp in vids:
        sign = vp.stem.upper()
        _process_one(vp, sign, "self", capture, args, writer)


def run_dataset(args, capture: Capture, writer: "ManifestWriter") -> None:
    rows = _read_label_csv(args.labels, args.col_file, args.col_gloss, args.col_signer)
    splits = _split_by_signer(rows, seed=args.seed)
    print(f"[dataset] {len(rows)} clips, {len(splits)} signers, split by signer")
    videos_dir = Path(args.videos)
    for r in rows:
        vp = videos_dir / r["file"]
        if not vp.exists():
            print(f"  ! missing video, skipping: {vp}")
            continue
        _process_one(vp, r["gloss"].upper(), r["signer"], capture, args, writer,
                     split=splits[r["signer"]])


def _process_one(vp: Path, sign: str, signer: str, capture: Capture, args,
                 writer: "ManifestWriter", split: str = "train") -> None:
    out_dir = Path(args.out) / sign
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{vp.stem}.json"
    clip_id = f"{sign}/{vp.stem}"

    if out_path.exists() and not args.force:
        print(f"  = skip (exists): {clip_id}")
        # Still record in manifest so a resumed run produces a complete manifest.
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        writer.add(clip_id, sign, signer, split, clip_stats(payload))
        return

    try:
        payload = extract_video(str(vp), capture, sign, apply_filter=not args.no_filter)
    except (IOError, OSError) as e:
        print(f"  ! failed {clip_id}: {e}")
        return

    out_path.write_text(json.dumps(payload), encoding="utf-8")
    stats = clip_stats(payload)
    writer.add(clip_id, sign, signer, split, stats)
    print(f"  + {clip_id}  frames={stats['n_frames']} cover={stats['hand_coverage']}")


# ----------------------------------------------------------------------------- helpers

def _read_label_csv(path: str, col_file: str, col_gloss: str,
                    col_signer: Optional[str]) -> list[dict]:
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append({
                "file": r[col_file],
                "gloss": r[col_gloss],
                "signer": r[col_signer] if col_signer else "unknown",
            })
    return rows


def _split_by_signer(rows: list[dict], seed: int = 42,
                     ratios=(0.70, 0.15, 0.15)) -> dict[str, str]:
    """Assign whole signers to train/val/test so no signer leaks across splits."""
    signers = sorted({r["signer"] for r in rows})
    rng = random.Random(seed)
    rng.shuffle(signers)
    n = len(signers)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    out: dict[str, str] = {}
    for i, s in enumerate(signers):
        out[s] = "train" if i < n_train else "val" if i < n_train + n_val else "test"
    return out


class ManifestWriter:
    """Accumulates rows and writes data/manifest.csv at the end."""

    def __init__(self, out_dir: str):
        self.path = Path(out_dir).parent / "manifest.csv"
        self.rows: list[dict] = []

    def add(self, clip_id, sign, signer, split, stats: dict) -> None:
        self.rows.append({
            "clip_id": clip_id, "sign": sign, "signer_id": signer, "split": split,
            **stats,
        })

    def flush(self) -> None:
        if not self.rows:
            print("manifest: no rows")
            return
        cols = ["clip_id", "sign", "signer_id", "split", "n_frames",
                "hand_coverage", "left_obs", "right_obs"]
        with open(self.path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(self.rows)
        print(f"manifest -> {self.path}  ({len(self.rows)} clips)")


# ----------------------------------------------------------------------------- cli

def main() -> None:
    p = argparse.ArgumentParser(description="Batch MediaPipe landmark extractor (-> Frame JSON).")
    sub = p.add_subparsers(dest="mode", required=True)

    pf = sub.add_parser("footage", help="extract from a folder where filename = sign")
    pf.add_argument("--src", required=True)
    pf.add_argument("--out", default="data/landmarks")
    pf.add_argument("--no-filter", action="store_true", help="skip the 1€ filter")
    pf.add_argument("--force", action="store_true", help="re-extract even if JSON exists")

    pd = sub.add_parser("dataset", help="extract ASL Citizen via a label CSV")
    pd.add_argument("--videos", required=True)
    pd.add_argument("--labels", required=True)
    pd.add_argument("--col-file", default="video_file")
    pd.add_argument("--col-gloss", default="gloss")
    pd.add_argument("--col-signer", default="participant_id")
    pd.add_argument("--seed", type=int, default=42)
    pd.add_argument("--out", default="data/landmarks")
    pd.add_argument("--no-filter", action="store_true")
    pd.add_argument("--force", action="store_true")

    args = p.parse_args()
    writer = ManifestWriter(args.out)
    with Capture() as capture:
        if args.mode == "footage":
            run_footage(args, capture, writer)
        else:
            run_dataset(args, capture, writer)
    writer.flush()


if __name__ == "__main__":
    main()
