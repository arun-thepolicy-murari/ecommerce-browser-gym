"""Calendar mutations — touch ONLY CalendarState.

Pure: no access to the shop / mail / food stores. The route handler does
any cross-app flash. Keeping these isolated is what makes the per-app
isolation test meaningful.
"""

from __future__ import annotations

from typing import Any

from server.apps.calendar.state import CalendarEvent, CalendarState


def check_availability(cal: CalendarState, day: str, start: str,
                       end: str) -> dict[str, Any]:
    """Free/busy check for a window. The branch condition for gated tasks."""
    return {"ok": True, "free": cal.is_free(day, start, end),
            "day": day, "window": f"{start}-{end}"}


def create_event(cal: CalendarState, *, title: str, day: str,
                 start: str, end: str, day_label: str = "") -> dict[str, Any]:
    title = (title or "").strip()
    if not title:
        return {"ok": False, "error": "a title is required"}
    if not day:
        return {"ok": False, "error": "a day is required"}
    eid = cal.new_id()
    cal.events[eid] = CalendarEvent(
        id=eid, title=title, day=day, day_label=day_label or day,
        start=start or "00:00", end=end or "00:00", source="user",
    )
    return {"ok": True, "event_id": eid, "title": title, "day": day}
