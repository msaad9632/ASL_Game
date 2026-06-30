"""C.1 acceptance check: replay an extracted clip JSON through the EXISTING verifier.

Proves the batch extractor's output is byte-compatible with the rule engine — same Frame
format the hand-recorded fixtures use. Prints the per-parameter scorecard for each clip.

    python -m tools.verify_extracted data/landmarks/HELLO/HELLO.json
    python -m tools.verify_extracted data/landmarks            # all clips under a dir
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.landmarks import Frame, RollingBuffer  # noqa: E402
from core.verifier import verify                  # noqa: E402
from signs import SIGNS                            # noqa: E402


def check_clip(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sign_name = payload["sign_name"]
    sign = SIGNS.get(sign_name)
    if sign is None:
        print(f"  ? {path.name}: no sign def for '{sign_name}' (skip)")
        return True  # not a failure of the format, just an unknown label (e.g. _COFFEE_A)

    # Wide window so the whole clip is retained; movement reads buffer start/end.
    buf = RollingBuffer(window_seconds=999.0)
    for fd in payload["frames"]:
        buf.add(Frame.from_dict(fd))

    res = verify(buf, sign)
    bar = "PASS" if res.passed else "----"
    scores = "  ".join(f"{p.name.split('_')[0]}={p.score:.2f}/{p.threshold:.2f}"
                       for p in res.params)
    print(f"  [{bar}] {sign_name:<10} {scores}")
    return True


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m tools.verify_extracted <clip.json | dir>")
        sys.exit(2)
    target = Path(sys.argv[1])
    clips = sorted(target.rglob("*.json")) if target.is_dir() else [target]
    print(f"verifying {len(clips)} clip(s) against the rule engine:")
    for c in clips:
        check_clip(c)


if __name__ == "__main__":
    main()
