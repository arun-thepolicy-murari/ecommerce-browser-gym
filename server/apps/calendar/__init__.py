"""Calendar app — an isolated calendar at the ``/calendar`` route family.

Owns its own store (:class:`server.apps.calendar.state.CalendarState`):
events with a day + time window, plus a free/busy check. Mutations touch
ONLY this store. Adds a fourth app to the workspace so tasks can gate on
availability ("if I'm free tomorrow evening, ...") — a new axis of hardness
on top of Shop / Mail / Food.
"""
