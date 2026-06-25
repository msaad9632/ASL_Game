"""Generic temporal verifier — one engine for every sign.

Implemented in Phase 3. verify(buffer, sign) returns a per-parameter confidence breakdown
{handshape, location, movement, orientation} in [0,1] PLUS an overall `passed`. `passed` is
True iff every parameter with required=True individually clears its threshold. There is no
averaging anywhere: a great handshape can never compensate for absent required movement.
"""
