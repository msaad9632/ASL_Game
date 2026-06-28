"""Lesson structure + game-flow state machine (shared across scenarios).

A Lesson is a list of Levels; each Level is a named list of Prompts (a sign + the on-screen
instruction). GameSession drives the flow: play a prompt, on a correct sign award points and
advance, finish a level (show a card), then the next level, then a finished summary. It is pure
state — no rendering, no recognition — so every scenario reuses it and only supplies its own
levels + theme.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.schema import Sign

POINTS_PER_SIGN = 10
SUCCESS_SECONDS = 1.4          # how long the "+10" celebration shows before advancing
LEVEL_CARD_SECONDS = 3.0       # how long the level-complete card shows


@dataclass(frozen=True)
class Prompt:
    sign: Sign
    text: str


@dataclass(frozen=True)
class Level:
    name: str
    prompts: list[Prompt]


@dataclass
class GameSession:
    """Tracks progress through a lesson. Call on_pass() when the verifier passes, update() each
    frame to advance timed transitions, and read .state to decide what to render."""

    levels: list[Level]
    level_idx: int = 0
    prompt_idx: int = 0
    level_score: int = 0           # points in the current level
    total_score: int = 0           # points across the whole lesson
    state: str = "playing"         # playing | success | level_complete | finished
    _t_state: float = 0.0          # when the current non-playing state began

    # ---- queries ----
    @property
    def level(self) -> Level:
        return self.levels[self.level_idx]

    @property
    def prompt(self) -> Prompt:
        return self.level.prompts[self.prompt_idx]

    @property
    def prompt_number(self) -> int:
        return self.prompt_idx + 1

    @property
    def level_len(self) -> int:
        return len(self.level.prompts)

    @property
    def level_max(self) -> int:
        return self.level_len * POINTS_PER_SIGN

    # ---- transitions ----
    def on_pass(self, now: float) -> None:
        """Called once when the active sign is recognized."""
        if self.state != "playing":
            return
        self.level_score += POINTS_PER_SIGN
        self.total_score += POINTS_PER_SIGN
        self.state = "success"
        self._t_state = now

    def update(self, now: float) -> None:
        """Advance timed transitions (success -> next prompt / level card -> next level)."""
        if self.state == "success" and now - self._t_state >= SUCCESS_SECONDS:
            if self.prompt_idx + 1 < self.level_len:
                self.prompt_idx += 1
                self.state = "playing"
            else:
                self.state = "level_complete"
                self._t_state = now
        elif self.state == "level_complete" and now - self._t_state >= LEVEL_CARD_SECONDS:
            if self.level_idx + 1 < len(self.levels):
                self.level_idx += 1
                self.prompt_idx = 0
                self.level_score = 0
                self.state = "playing"
            else:
                self.state = "finished"
                self._t_state = now

    def success_progress(self, now: float) -> float:
        return min(1.0, (now - self._t_state) / SUCCESS_SECONDS) if self.state == "success" else 0.0
