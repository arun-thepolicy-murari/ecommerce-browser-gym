"""Calendar app routes — the ``/calendar`` route family.

Same injected-deps pattern as Mail/Food (no circular import).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.apps.calendar import mutations as C
from server.apps.calendar.state import TODAY, TOMORROW

router = APIRouter(prefix="/calendar", tags=["calendar"])

_deps: dict[str, Any] = {}


def configure(*, templates, get_world, build_ctx, flash) -> None:
    _deps.update(templates=templates, get_world=get_world,
                 build_ctx=build_ctx, flash=flash)


def _render(request: Request, name: str, **extra):
    ctx = _deps["build_ctx"](request, active_app="calendar", **extra)
    return _deps["templates"].TemplateResponse(request, name, ctx)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def agenda(request: Request):
    cal = _deps["get_world"]().calendar
    # Group events by day_label, in day/time order.
    days: dict[str, list] = {}
    for e in cal.ordered():
        days.setdefault(e.day_label, []).append(e)
    return _render(request, "calendar/agenda.html", calendar=cal, days=days)


@router.get("/new", response_class=HTMLResponse)
async def new_event(request: Request, day: str = "", title: str = ""):
    cal = _deps["get_world"]().calendar
    return _render(request, "calendar/new_event.html", calendar=cal,
                   day_prefill=day, title_prefill=title,
                   today=TODAY, tomorrow=TOMORROW)


@router.post("/create")
async def create(
    request: Request,
    title: str = Form(""),
    day: str = Form(""),
    start: str = Form("19:00"),
    end: str = Form("20:00"),
):
    world = _deps["get_world"]()
    day_label = ("Tomorrow (Fri May 22)" if day == TOMORROW
                 else ("Today (Thu May 21)" if day == TODAY else day))
    r = C.create_event(world.calendar, title=title, day=day,
                       start=start, end=end, day_label=day_label)
    if r.get("ok"):
        _deps["flash"](world.shop, "success",
                       f"Added '{r['title']}' to your calendar.")
        return RedirectResponse("/calendar", 303)
    _deps["flash"](world.shop, "error", r.get("error", "Could not add event."))
    return RedirectResponse("/calendar/new", 303)
