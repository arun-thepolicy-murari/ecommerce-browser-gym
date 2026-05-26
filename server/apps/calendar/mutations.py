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


def update_event(cal: CalendarState, event_id: str, *, start: str = "",
                 end: str = "", title: str = "") -> dict[str, Any]:
    """Move/retitle an existing event IN PLACE — the same event keeps its id.
    This is the path an agent takes to push a reminder to a new time WITHOUT
    leaving the old one behind (the M16 'don't over-keep' negative action)."""
    e = cal.events.get(event_id)
    if e is None:
        return {"ok": False, "error": "no such event"}
    if start:
        e.start = start
    if end:
        e.end = end
    if title.strip():
        e.title = title.strip()
    return {"ok": True, "event_id": event_id, "start": e.start, "end": e.end}


def delete_event(cal: CalendarState, event_id: str) -> dict[str, Any]:
    """Remove an event entirely. The other way to avoid an over-kept stale
    reminder: delete the old one and create a fresh one at the new time."""
    if event_id not in cal.events:
        return {"ok": False, "error": "no such event"}
    removed = cal.events.pop(event_id)
    return {"ok": True, "event_id": event_id, "title": removed.title}
