"""Shared sign definitions (pure data) — reused across all scenarios.

Import a sign directly (``from signs.coffee import COFFEE``) or look it up by name in the
SIGNS registry (handy for scenarios that drive prompts by sign name).
"""
from signs.coffee import COFFEE
from signs.letter_a import LETTER_A
from signs.please import PLEASE
from signs.thank_you import THANK_YOU

SIGNS = {
    COFFEE.name: COFFEE,
    LETTER_A.name: LETTER_A,
    PLEASE.name: PLEASE,
    THANK_YOU.name: THANK_YOU,
}

__all__ = ["COFFEE", "LETTER_A", "PLEASE", "THANK_YOU", "SIGNS"]
