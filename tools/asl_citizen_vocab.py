"""Maps ASL Citizen glosses -> our game sign ids (Phase C staging: game vocab first).

ASL Citizen labels lexical signs by gloss with sense numbers (WANT1, DOCTOR2, HOSPITAL1).
We fold sense variants of the same word into one game label — a recognition model SHOULD accept
either valid production of "WANT". Synonyms that are genuinely different lexemes (HURT vs PAIN)
are excluded to keep labels clean. EMERGENCY/FEVER and the fingerspelled letters are not in
ASL Citizen (it's a lexical dictionary, not fingerspelling), so they stay rule-only for now.

Keys are the exact ASL Citizen `Gloss` values; values are our engine sign names.
"""

GAME_VOCAB: dict[str, str] = {
    "HELLO": "HELLO",
    "PLEASE": "PLEASE",
    "THANKYOU": "THANK_YOU",
    "YOU": "YOU",
    "COFFEE": "COFFEE",
    "WANT1": "WANT",
    "WANT2": "WANT",
    "YES": "YES",
    "HELP": "HELP",
    "PAIN": "PAIN",
    "MEDICINE": "MEDICINE",
    "DOCTOR1": "DOCTOR",
    "DOCTOR2": "DOCTOR",
    "NURSE": "NURSE",
    "SICK": "SICK",
    "WATER": "WATER",
    "BREATHE": "BREATHE",
    "HOSPITAL1": "HOSPITAL",
    "HOSPITAL2": "HOSPITAL",
    "DIZZY": "DIZZY",
}
