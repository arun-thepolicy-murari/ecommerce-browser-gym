"""Food-delivery app — an isolated food-ordering site at ``/food``.

Owns its own store (:class:`server.apps.food.state.FoodState`). Placing a
food order EMITS a ``FoodOrderPlaced`` event on the bus; the subscriber
lands a receipt email in Mail (and, in Phase 2, a delivery slot on the
Calendar). The food mutation never writes Mail directly — that is the
event bus's job.
"""
