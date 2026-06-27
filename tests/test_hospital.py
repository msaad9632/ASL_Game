"""Hospital scenario confusor regression tests.

Mirrors tests/test_coffee.py for every hospital movement sign. For each sign we replay two
committed fixtures through the SAME generic verifier:

  - <name>_correct.json  -> must PASS, with the movement parameter clearing its threshold.
  - <name>_confusor.json -> must FAIL, specifically because MOVEMENT is below threshold (the
    learner froze the correct pose). Handshape/location are NOT the reason it fails.

This is the real prevention mechanism for the single-frame bug: if anyone later weakens a
movement check or the schema guard, these tests fail loudly. Fixtures that have not been recorded
yet are skipped (so the suite stays green during incremental recording), but a sign whose
`correct` fixture exists MUST also ship a `confusor`, and vice-versa.

Record fixtures with:
    python -m tools.record_fixture --name help_correct  --seconds 3 --sign HELP
    python -m tools.record_fixture --name help_confusor --seconds 3 --sign HELP   # hold it FROZEN
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.landmarks import Frame, RollingBuffer
from core.verifier import verify
from signs import HELP, PAIN, MEDICINE, EMERGENCY

FIXTURES = Path(__file__).parent / "fixtures"

# (sign object, fixture base name). Each ships a <base>_correct and <base>_confusor fixture.
HOSPITAL_SIGNS = [
    (HELP, "help"),
    (PAIN, "pain"),
    (MEDICINE, "medicine"),
    (EMERGENCY, "emergency"),
]


def _fixture_path(base: str, kind: str) -> Path:
    return FIXTURES / f"{base}_{kind}.json"


def _load_buffer(base: str, kind: str) -> RollingBuffer:
    with open(_fixture_path(base, kind)) as fh:
        data = json.load(fh)
    buf = RollingBuffer(window_seconds=5.0)
    for fd in data["frames"]:
        buf.add(Frame.from_dict(fd))
    return buf


def _require(base: str, kind: str) -> RollingBuffer:
    path = _fixture_path(base, kind)
    if not path.exists():
        pytest.skip(f"fixture not recorded yet: {path.name}")
    return _load_buffer(base, kind)


@pytest.mark.parametrize("sign,base", HOSPITAL_SIGNS, ids=[s.name for s, _ in HOSPITAL_SIGNS])
class TestCorrect:
    """The correctly-performed sign must pass, and its movement must clear threshold."""

    def test_overall_pass(self, sign, base):
        result = verify(_require(base, "correct"), sign)
        assert result.passed, (
            f"{sign.name} correct should pass but failed on: {result.failing_required}"
        )

    def test_movement_clears_threshold(self, sign, base):
        result = verify(_require(base, "correct"), sign)
        m = result.get("movement")
        assert m is not None and m.score >= m.threshold, (
            f"{sign.name} correct movement should clear: {m.score:.2f} < {m.threshold:.2f}"
        )


@pytest.mark.parametrize("sign,base", HOSPITAL_SIGNS, ids=[s.name for s, _ in HOSPITAL_SIGNS])
class TestConfusor:
    """The frozen pose — correct handshape, no motion — must fail ON MOVEMENT specifically."""

    def test_overall_fail(self, sign, base):
        result = verify(_require(base, "confusor"), sign)
        assert not result.passed, f"{sign.name} frozen confusor must NOT pass"

    def test_fails_on_movement(self, sign, base):
        result = verify(_require(base, "confusor"), sign)
        assert "movement" in result.failing_required, (
            f"{sign.name} confusor should fail on movement, "
            f"but failing_required={result.failing_required}"
        )

    def test_movement_below_threshold(self, sign, base):
        result = verify(_require(base, "confusor"), sign)
        m = result.get("movement")
        assert m is not None and m.score < m.threshold, (
            f"{sign.name} confusor movement should be below threshold: "
            f"{m.score:.2f} >= {m.threshold:.2f}"
        )


@pytest.mark.parametrize("sign,base", HOSPITAL_SIGNS, ids=[s.name for s, _ in HOSPITAL_SIGNS])
class TestIdle:
    """The cardinal false-positive case: hands present in roughly the right handshape but the user
    is NOT performing the sign — only incidental jitter. Must never pass, and must fail on movement
    (it is the absence of the real motion that disqualifies it, not the handshape)."""

    def test_overall_fail(self, sign, base):
        result = verify(_require(base, "idle"), sign)
        assert not result.passed, (
            f"{sign.name} idle (present but not signing) must NOT pass — "
            f"scores={[(p.name, round(p.score, 2)) for p in result.params]}"
        )

    def test_fails_on_movement(self, sign, base):
        result = verify(_require(base, "idle"), sign)
        m = result.get("movement")
        assert m is not None and m.score < m.threshold, (
            f"{sign.name} idle movement should be below threshold: {m.score:.2f} >= {m.threshold:.2f}"
        )
