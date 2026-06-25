# Hospital Scenario — Getting Started

## Prompt to paste into Claude (copy everything below the line)

---

I'm building the **hospital scenario** for an ASL learning game. My teammate (Saad) already
built the shared recognition engine in `core/` and the coffee-shop scenario. I need to build
the hospital scenario in `scenarios/hospital_shop/`.

**Read `CLAUDE.md` in the repo root first** — it has the full architecture and the non-negotiable
rules. Here's what matters for me specifically:

### What's already built (DO NOT rewrite or duplicate)

- `core/` — the shared recognition engine (capture, verifier, movement detection, handshape
  scoring). **I import this, I don't copy it.** Every scenario uses the same verifier so bugs
  stay fixed everywhere.
- `core/schema.py` — the Sign Definition Schema. Every sign is declared as a dataclass with
  required handshape, location, movement, orientation, and NMM parameters.
- `core/verifier.py` — `verify(buffer, sign)` returns per-parameter scores. A sign passes ONLY
  when every required parameter individually clears its threshold. No averaging.
- `core/movement.py` — movement detectors (circular, linear, repeated). Already calibrated
  on real hands. Key settings live in the sign definitions, not in the engine.
- `signs/` — shared sign definitions. If the hospital scenario uses a sign that already exists
  here (like COFFEE), just import it.

### Where movement calibration lives

Movement thresholds are **per-sign**, set in the sign definition files in `signs/`. Example
from `signs/coffee.py`:

```python
movement=MovementReq(
    kind=MovementKind.CIRCULAR,
    min_total_rotation_deg=270.0,   # accumulated rotation needed
    radius_tolerance_ratio=0.6,     # how messy the circle can be
    min_duration_s=0.6,             # minimum motion duration
    required=True,                  # MUST be checked — cannot be bypassed
)
```

The engine-level setting `_RADIUS_CV_FREE = 0.30` in `core/movement.py` gives full radius
credit until the coefficient of variation exceeds 0.30 (a human grind is never perfect). This
was calibrated on real hands — **do not change it** unless you have a specific reason.

### What I need to build

1. **`scenarios/hospital_shop/scene.py`** — hospital-themed background, prompts, success
   animations. Use `core/game.py` for shared mechanics (PiP webcam, score HUD, success flash).
2. **`scenarios/hospital_shop/main.py`** — thin entry point: webcam → buffer → verifier → scene.
3. **New sign definitions** in `signs/` for hospital vocabulary (e.g. HELP, HURT, DOCTOR,
   MEDICINE). Each sign needs:
   - A definition in `signs/<name>.py` using the schema
   - A correct-sign fixture + a confusor fixture in `tests/fixtures/`
   - A test in `tests/` asserting correct passes and confusor fails **on the right parameter**
4. **`scenarios/hospital_shop/assets/`** — hospital background image (procedural fallback if absent).

### How to add a sign safely

Use the existing Prompt 5 workflow from `CLAUDE.md`:
1. Write the sign definition in `signs/<name>.py`
2. The schema will **reject** any sign that declares movement but marks it not-required (the
   structural guard — try it and see the error)
3. Record correct + confusor fixtures with `python -m tools.record_fixture`
4. Add a test asserting the confusor fails specifically on the right parameter
5. Test live: `python -m tools.demo_verify --sign <NAME>`

### Rules

- **Never duplicate `core/` logic** in my scenario folder — import it
- **Never approve a movement sign from a single frame** — the schema prevents this structurally
- **Push to a feature branch**, not main (e.g. `git checkout -b hospital/<topic>`)
- **Test each sign live** with `demo_verify` before merging

### Run the demo to see how it works

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Download models (see models/README.md)
python -m tools.demo_verify --sign COFFEE    # see Saad's sign working live
```
