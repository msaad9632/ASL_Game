# ASL_Game

A gamified **American Sign Language (ASL)** learning app. The player is shown a prompt inside a
themed scenario (a coffee shop, a hospital, …) and must perform the correct ASL sign in front of
their webcam to progress.

## How recognition works (and the bug we refuse to repeat)

Every ASL sign is defined by five parameters: **handshape, location, movement, palm orientation,
non-manual markers**. Recognition is **rule-based geometry** over MediaPipe hand + pose
landmarks — no trained ML model in v1, and no commercially restricted datasets.

The cardinal rule: **a sign that requires movement is never approved from a single frame.**
Movement is measured over a rolling ~1.5–2 second window of frames. (An earlier version passed
COFFEE for two motionless fists because it only inspected one frame — that class of bug is now
structurally prevented. See [CLAUDE.md](CLAUDE.md).)

## Project structure

```
ASL_Game/
├── core/            # SHARED recognition engine (never duplicated per scenario)
├── signs/           # sign definitions as data
├── scenarios/
│   ├── coffee_shop/   # Saad's themed scenario (presentation + assets only)
│   └── hospital_shop/ # teammate's themed scenario
├── tools/           # landmark fixture recorder
├── tests/           # confusor regression tests
└── models/          # MediaPipe .task model files (downloaded, git-ignored)
```

`core/` does recognition and is shared by every scenario. `scenarios/<name>/` only owns its
look (background, prompts, animations). This split is deliberate — see [CLAUDE.md](CLAUDE.md).

## Setup

1. Python **3.10+**.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows:        .venv\Scripts\activate
   # macOS / Linux:  source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Download the MediaPipe Tasks model files (one-time) into `models/` — see
   [models/README.md](models/README.md).

## Running

> Webcam scenarios arrive in a later build phase. Once available:
```bash
python -m scenarios.coffee_shop.main --debug
```

## Tests

```bash
pytest
```

## Adding a new sign (safe workflow)

1. Write the definition in `signs/<name>.py`, marking **every** parameter the sign requires.
2. Record a **correct** fixture AND a **confusor** (the likeliest accidental false positive)
   with `python -m tools.record_fixture`.
3. Add a test asserting correct → **PASS** and confusor → **FAIL on the right parameter**.
4. Run the pre-ship checklist in [CLAUDE.md](CLAUDE.md) before merging.

## Roadmap

- **v1 (now):** rule-based math, Python desktop, scenario by scenario.
- **Later:** port recognition to the browser (MediaPipe Tasks Vision / TypeScript), add
  Supabase for user progress, and move to an LSTM/GRU once the vocabulary outgrows
  hand-written rules.
