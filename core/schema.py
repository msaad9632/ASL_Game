"""Sign Definition Schema — every sign declared as data.

Implemented in Phase 2. Dataclasses for the five ASL parameters (handshape per hand, location,
movement, palm orientation, NMM), each carrying a `required` flag. Movement is a typed field
(none/linear/circular/repeated) with numeric thresholds. The schema is what makes it
structurally impossible for a movement-requiring sign to pass on handshape + location alone.
"""
