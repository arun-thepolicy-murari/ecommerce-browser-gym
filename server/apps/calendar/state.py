"""Calendar app store — CalendarState + CalendarEvent.

Wholly separate from the other apps. Fixed "today"/"tomorrow" dates so a
reset for a given seed reproduces an identical calendar (the
environment-correctness gate requires deterministic episodes).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# The gym's fixed "now". TODAY matches the Mail/Food SEED_DATE.
TODAY = "2026-05-21"
TOMORROW = "2026-05-22"


@dataclass
class CalendarEvent:
    id: str
    title: str
    day: str                 # "2026-05-22"
    day_label: str           # "Tomorrow (Fri May 22)"
    start: str               # "14:00"
    end: str                 # "15:00"
    source: str = "seed"     # seed | user | food | shop


@dataclass
class CalendarState:
    events: dict[str, CalendarEvent] = field(default_factory=dict)
    account_name: str = "Alice Anderson"
    _next: int = 1

    def new_id(self) -> str:
        eid = f"ev_{self._next}"
        self._next += 1
        return eid

    def ordered(self) -> list[CalendarEvent]:
        return sorted(self.events.values(), key=lambda e: (e.day, e.start))

    def is_free(self, day: str, start: str, end: str) -> bool:
        """True iff no event overlaps [start, end) on `day` (HH:MM strings,
        comparable lexically)."""
        for e in self.events.values():
            if e.day != day:
                continue
            if start < e.end and e.start < end:   # overlap
                return False
        return True

    def to_json(self) -> dict[str, Any]:
        return {
            "events": {k: asdict(v) for k, v in self.events.items()},
            "today": TODAY, "tomorrow": TOMORROW,
        }


def make_calendarstate(seed: int = 0) -> CalendarState:
    """Seed a non-empty calendar. Critically, TOMORROW EVENING (19:00) is
    FREE — there's a 2pm meeting tomorrow and an event today, so the agent
    must check the SPECIFIC evening window rather than assume busy/free."""
    c = CalendarState()
    for title, day, dl, s, e in [
        ("Gym session", TODAY, "Today (Thu May 21)", "18:00", "19:00"),
        ("Team sync", TOMORROW, "Tomorrow (Fri May 22)", "14:00", "15:00"),
        ("Dentist", TOMORROW, "Tomorrow (Fri May 22)", "10:00", "10:45"),
    ]:
        eid = c.new_id()
        c.events[eid] = CalendarEvent(id=eid, title=title, day=day,
                                      day_label=dl, start=s, end=e,
                                      source="seed")
    return c
