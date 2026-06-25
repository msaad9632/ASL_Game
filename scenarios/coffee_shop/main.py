"""Coffee-shop scenario entry point.

Implemented in Phase 5. Thin loop: read webcam -> core.capture -> fill core RollingBuffer ->
core.verifier.verify(active_sign) -> drive the coffee-shop game scene (scene.py). Success state
fires only on an overall pass. Run with --debug to show live per-parameter scores.

    python -m scenarios.coffee_shop.main --debug
"""
