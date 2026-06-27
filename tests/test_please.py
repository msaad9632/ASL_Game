"""PLEASE confusor regression test.

PLEASE = an open hand circling on the chest. The confusor is an open hand held still on the
chest — correct handshape and location, but no movement. It must FAIL specifically on movement,
proving the single-frame guarantee holds for this sign too (not just COFFEE).
"""
from __future__ import annotations

import json
from pathlib import Path

from core.landmarks import Frame, RollingBuffer
from core.verifier import verify
from signs import PLEASE

FIXTURES = Path(__file__).parent / "fixtures"


def _load_buffer(name: str) -> RollingBuffer:
    with open(FIXTURES / f"{name}.json") as fh:
        data = json.load(fh)
    buf = RollingBuffer(window_seconds=5.0)
    for fd in data["frames"]:
        buf.add(Frame.from_dict(fd))
    return buf


class TestPleaseCorrect:
    def test_overall_pass(self):
        result = verify(_load_buffer("please_correct"), PLEASE)
        assert result.passed, f"Correct PLEASE should pass; failing={result.failing_required}"

    def test_movement_clears(self):
        m = verify(_load_buffer("please_correct"), PLEASE).get("movement")
        assert m.score >= m.threshold, f"movement {m.score:.2f} < {m.threshold:.2f}"

    def test_handshape_open(self):
        p = verify(_load_buffer("please_correct"), PLEASE).get("handshape_dominant")
        assert p.cleared, f"open handshape should clear: {p.score:.2f}"


class TestPleaseConfusor:
    def test_overall_fail(self):
        assert not verify(_load_buffer("please_confusor"), PLEASE).passed

    def test_fails_on_movement(self):
        result = verify(_load_buffer("please_confusor"), PLEASE)
        assert "movement" in result.failing_required, (
            f"confusor should fail on movement; failing={result.failing_required}"
        )

    def test_handshape_still_good(self):
        """The confusor has a correct open hand — it fails ONLY because of movement."""
        p = verify(_load_buffer("please_confusor"), PLEASE).get("handshape_dominant")
        assert p.cleared, f"confusor handshape should still be good: {p.score:.2f}"


class TestPleaseWrongLocation:
    """The same open-hand circle, but on the BELLY instead of the chest, must fail on location.

    This is what makes PLEASE teach the *right* sign: correct handshape and correct movement
    can't bypass the location parameter. (PLEASE is defined on the chest, not the belly.)
    """

    def test_belly_fails_on_location(self):
        result = verify(_load_buffer("please_belly"), PLEASE)
        assert not result.passed, "PLEASE on the belly must not pass"
        assert "location" in result.failing_required, (
            f"belly should fail on location; failing={result.failing_required}"
        )

