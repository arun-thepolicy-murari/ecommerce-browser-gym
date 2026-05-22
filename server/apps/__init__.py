"""Multi-app layer.

The single e-commerce shop (``server.state.GymState``) is now ONE app in a
multi-app world. Each app owns its OWN isolated store; the only channel for
cross-app effects is the append-only event log in ``server.apps.bus``.

``server.apps.world.WorldState`` wraps the existing ``GymState`` (the shop)
together with the new per-app stores (mail / food / calendar). The existing
``GymState`` is NOT modified or renamed — every existing single-app task,
verifier, oracle and test keeps working unchanged.
"""
