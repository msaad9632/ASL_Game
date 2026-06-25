"""COFFEE confusor regression test.

Implemented in Phase 4. Replays two fixtures through the verifier:
  - coffee_correct.json  -> must PASS, with movement confidence clearing threshold.
  - coffee_confusor.json -> must FAIL, specifically because the MOVEMENT parameter is below
    threshold (asserted by parameter, not just an overall fail).

This is the real prevention mechanism for the original single-frame bug: it fails loudly if
anyone later weakens the movement check.
"""

import pytest


@pytest.mark.skip(reason="Implemented in Phase 4 (recorder + confusor fixtures).")
def test_coffee_confusor_placeholder():
    pass
