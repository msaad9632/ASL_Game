"""Download WLASL clips for the game vocabulary and extract landmarks (-> Frame JSON).

WLASL ships metadata only (gloss -> instances with a source URL + frame range); the videos must
be fetched from YouTube and various ASL dictionary sites. Expect partial yield — WLASL is ~5
years old and many source URLs are dead. We skip failures and log coverage.

Pipeline mirrors tools/extract_dataset.py and emits the SAME Frame JSON format, so the dataset
builder / verifier / inspector all consume WLASL exactly like ASL Citizen.

    python -m tools.wlasl_extract --meta data/wlasl/WLASL_v0.3.json --out data/wlasl/landmarks

Resumable: an instance whose output JSON already exists is skipped.
⚠️ WLASL licensing is non-commercial/research — see CLAUDE.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import cv2
    import requests
except ImportError as exc:  # pragma: no cover
    raise ImportError("wlasl_extract needs opencv-python + requests") from exc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.capture import Capture                                  # noqa: E402
from tools.extract_dataset import _smooth_hands_inplace, clip_stats, ManifestWriter  # noqa: E402
from tools.wlasl_vocab import WLASL_VOCAB                         # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def download(url: str, dest: str) -> bool:
    """Fetch one clip to `dest`. YouTube via yt-dlp; everything else via direct GET."""
    if "youtube.com" in url or "youtu.be" in url:
        cmd = [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings",
               "-f", "mp4/best", "--no-playlist", "-o", dest, url]
        try:
            subprocess.run(cmd, capture_output=True, timeout=150, check=False)
        except subprocess.TimeoutExpired:
            return False
        return os.path.exists(dest) and os.path.getsize(dest) > 1000
    try:
        r = requests.get(url, timeout=60, stream=True, headers={"User-Agent": UA})
        if r.status_code != 200:
            return False
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return os.path.getsize(dest) > 1000
    except Exception:
        return False


def extract_range(path: str, capture: Capture, sign: str,
                  frame_start: int, frame_end: int) -> dict | None:
    """Run MediaPipe over [frame_start, frame_end] (1-based; -1 end = whole clip)."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if fps <= 1e-3:
        fps = 25.0
    start = max(0, frame_start - 1) if frame_start and frame_start > 0 else 0
    end = frame_end if (frame_end and frame_end > 0) else 10 ** 9

    frames = []
    idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok or idx >= end:
            break
        if idx >= start:
            t = (idx - start) / fps
            frames.append(capture.process(bgr, int(t * 1000), t))
        idx += 1
    cap.release()
    if not frames:
        return None
    _smooth_hands_inplace(frames)
    return {"sign_name": sign, "frames": [f.to_dict() for f in frames]}


def main() -> None:
    ap = argparse.ArgumentParser(description="Download + extract WLASL game-vocab clips.")
    ap.add_argument("--meta", default="data/wlasl/WLASL_v0.3.json")
    ap.add_argument("--out", default="data/wlasl/landmarks")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    data = json.load(open(args.meta, encoding="utf-8"))
    # Flatten to (sign, instance) for our vocab only.
    jobs = []
    for entry in data:
        sign = WLASL_VOCAB.get(entry["gloss"])
        if not sign:
            continue
        for inst in entry["instances"]:
            jobs.append((sign, inst))
    print(f"[wlasl] {len(jobs)} instances across {len(set(s for s, _ in jobs))} signs")

    writer = ManifestWriter(args.out)
    ok = fail = skip = 0
    with Capture() as capture:
        for sign, inst in jobs:
            vid = str(inst.get("video_id") or inst.get("url", "").split("/")[-1].split("?")[0])
            split = inst.get("split", "train")
            out_dir = Path(args.out) / sign
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{vid}.json"
            clip_id = f"{sign}/{vid}"

            if out_path.exists() and not args.force:
                payload = json.loads(out_path.read_text(encoding="utf-8"))
                writer.add(clip_id, sign, f"wlasl_{inst.get('signer_id', '?')}", split, clip_stats(payload))
                skip += 1
                continue

            tmp = os.path.join(tempfile.gettempdir(), f"wlasl_{vid}.mp4")
            try:
                if not download(inst["url"], tmp):
                    fail += 1
                    continue
                payload = extract_range(tmp, capture, sign,
                                        inst.get("frame_start", 1), inst.get("frame_end", -1))
                if payload is None or not any(fr["hands"] for fr in payload["frames"]):
                    fail += 1
                    continue
                out_path.write_text(json.dumps(payload), encoding="utf-8")
                stats = clip_stats(payload)
                writer.add(clip_id, sign, f"wlasl_{inst.get('signer_id', '?')}", split, stats)
                ok += 1
                print(f"  + {clip_id} frames={stats['n_frames']} cover={stats['hand_coverage']}")
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    writer.flush()
    print(f"[wlasl] done: ok={ok} fail={fail} skip={skip} (yield {ok}/{ok + fail} downloadable)")


if __name__ == "__main__":
    main()
